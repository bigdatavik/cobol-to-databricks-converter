"""
COBOL to Databricks Converter - Databricks App

A Streamlit application deployed as a Databricks App that converts COBOL mainframe code to
PySpark or SQL using Databricks Foundation Models (Claude Sonnet 4.5).

Features:
- Multi-source input: Local upload, Workspace folders, Unity Catalog volumes
- Per-user customizable assistant instructions
- Flexible output: Save to custom folders in user's workspace
"""

import streamlit as st
import sys
import os
import datetime
import re
import time
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.workspace import ImportFormat, Language
from openai import OpenAI

# Import utility functions from local modules
from file_handler import (
    validate_sas_file as validate_cobol_file,  # Reuse for COBOL
    extract_metadata,
    estimate_conversion_complexity,
    format_sas_code_preview as format_cobol_code_preview
)
from utils import (
    calculate_stats,
    generate_report,
    extract_code_blocks,
    validate_conversion,
    format_file_size
)

# Page configuration
st.set_page_config(
    page_title="COBOL to Databricks Converter",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #FF3621;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'cobol_files' not in st.session_state:
    st.session_state.cobol_files = []
if 'conversion_results' not in st.session_state:
    st.session_state.conversion_results = []
if 'show_instructions' not in st.session_state:
    st.session_state.show_instructions = False

# Get Databricks configuration
cfg = Config()

# Get current user (for display purposes only)
try:
    w = WorkspaceClient()
    current_user = w.current_user.me()
    username = current_user.user_name
    user_prefix = os.getenv("USER_PREFIX", username.split('@')[0].split('.')[0].lower() + "cbl")
except:
    username = "app-user"
    user_prefix = "defaultcbl"

# Get token for Foundation Models API
# For OpenAI client, we need an actual string token
# Use the pattern from MY_ENVIRONMENT: cfg.authenticate is a callable
try:
    # Get the token by calling the authenticate method
    auth_headers = cfg.authenticate()
    if isinstance(auth_headers, dict) and 'Authorization' in auth_headers:
        # Extract token from Authorization header (format: "Bearer <token>")
        databricks_token = auth_headers['Authorization'].replace('Bearer ', '')
    else:
        # Try direct token access
        databricks_token = cfg.token
        if not databricks_token:
            # Last resort: use WorkspaceClient token
            databricks_token = w.config.token
except Exception as e:
    st.error(f"   Token retrieval error: {e}")
    databricks_token = None

# Configuration
DATABRICKS_HOST = cfg.host  # Use cfg.host directly (don't strip https://)
SERVING_ENDPOINT = f"{DATABRICKS_HOST}/serving-endpoints"
MODEL_NAME = os.getenv("SERVING_ENDPOINT_NAME", "databricks-claude-sonnet-4-5")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8000"))  # Configurable via app.yaml


@st.cache_data
def load_instructions():
    """Load COBOL assistant instructions from app bundle"""
    # Load from app bundle (deployed with the app)
    instructions_path = os.path.join(os.path.dirname(__file__), "config", ".assistant_instructions_cobol.md")
    
    try:
        with open(instructions_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback: try to load from bundle root
        alt_path = "config/.assistant_instructions_cobol.md"
        try:
            with open(alt_path, 'r') as f:
                return f.read()
        except Exception as e:
            st.error(f"   Could not load COBOL assistant instructions: {e}")
            return """# COBOL to Databricks Migration Instructions

## Environment
- Source: {user_prefix}_payer_dev.analytics_gold.*
- Target: {user_prefix}_payer_analyst_dev

Use 3-level namespace for all table references.
Follow snake_case naming conventions.
Convert COBOL PERFORM to PySpark transformations.
"""


class CodeValidator:
    """Validates generated code for common COBOL to PySpark/SQL conversion errors"""
    
    def __init__(self):
        # Define validation patterns - easy to add/remove/enable/disable
        self.patterns = {
            'python_boolean_in_when': {
                'regex': r'F\.when\(\s*\w+\s*[><=!]+',
                'severity': 'HIGH',
                'fix': 'F.when() expects Column expressions. Use F.lit() for Python values.',
                'example_wrong': 'F.when(completed_count > 0, ...)',
                'example_right': 'F.when(F.lit(completed_count) > 0, ...)',
                'enabled': True,
                'applies_to': ['PySpark']
            },
            'missing_cast_aggregation': {
                'regex': r'F\.(sum|avg|min|max|percentile_approx|stddev|variance|count|countDistinct)\([^)]+\)(?!\s*\.cast)',
                'severity': 'HIGH',
                'fix': 'ALL aggregations must be cast immediately to avoid type errors.',
                'example_wrong': 'F.avg("days").alias("avg_days")',
                'example_right': 'F.avg("days").cast("double").alias("avg_days")',
                'enabled': True,
                'applies_to': ['PySpark']
            },
            'casting_date_columns': {
                'regex': r'(F\.to_date|CAST\([^)]*date[^)]*AS DATE)',
                'severity': 'MEDIUM',
                'fix': 'Gold table date columns are already DATE type. Do not cast.',
                'example_wrong': 'F.to_date(F.col("approval_date"))',
                'example_right': 'F.col("approval_date")  # Already DATE',
                'enabled': True,
                'applies_to': ['PySpark', 'SQL']
            },
            'ambiguous_select_star': {
                'regex': r'SELECT\s+\*.*?FROM.*?(?:WHERE|GROUP|ORDER|$)',
                'severity': 'MEDIUM',
                'fix': 'Check for ambiguous column references in SELECT * with derived columns.',
                'example_wrong': 'SELECT *, turnaround_days AS turnaround_days (or other duplicate columns)',
                'example_right': 'SELECT * REPLACE (new_value AS existing_column) or list columns explicitly',
                'enabled': False,  # Disabled - allowing pure SQL now
                'applies_to': ['SQL']
            },
            'unused_pyspark_import_in_sql': {
                'regex': r'from pyspark\.sql import.*?F\b',
                'severity': 'LOW',
                'fix': 'Remove unused PySpark imports in SQL mode - all logic should be in SQL.',
                'example_wrong': 'from pyspark.sql import functions as F (then never use F)',
                'example_right': 'Remove the import - use pure SQL instead',
                'enabled': False,  # Disabled
                'applies_to': ['SQL']
            },
            'pure_sql_in_mixed_mode': {
                'regex': r'spark\.sql\s*\(\s*f?["\'"]{3}\s*CREATE\s+OR\s+REPLACE\s+TABLE.*?SELECT\s+\*\s*,',
                'severity': 'HIGH',
                'fix': 'FORBIDDEN PATTERN! Use PySpark DataFrame API instead: df = spark.table(...); df = df.withColumn(...); df.write.saveAsTable(...)',
                'example_wrong': 'spark.sql(f"""CREATE OR REPLACE TABLE ... AS SELECT *, col AS col FROM ...""")',
                'example_right': 'df = spark.table(f"{source_catalog}.{source_schema}.table"); df = df.withColumn("col", ...); df.write.saveAsTable(...)',
                'enabled': False,  # Disabled - allowing pure SQL now
                'applies_to': ['SQL'],
                'multiline': True
            },
            'persist_or_cache': {
                'regex': r'\.(persist|cache)\(',
                'severity': 'MEDIUM',
                'fix': 'Do not use .persist() or .cache() - not supported on serverless.',
                'example_wrong': 'df.persist()',
                'example_right': '# Remove .persist() - not needed',
                'enabled': True,
                'applies_to': ['PySpark']
            }
        }
    
    def validate(self, code, output_type):
        """
        Validate generated code and return list of errors found
        
        Args:
            code: Generated PySpark or SQL code
            output_type: "PySpark" or "SQL"
            
        Returns:
            List of error dictionaries with type, severity, fix, examples
        """
        import re
        errors = []
        
        for name, pattern in self.patterns.items():
            # Skip if pattern not enabled
            if not pattern['enabled']:
                continue
            
            # Skip if pattern doesn't apply to this output type
            if output_type not in pattern['applies_to']:
                continue
            
            # Check if pattern matches
            if re.search(pattern['regex'], code, re.IGNORECASE | re.MULTILINE):
                errors.append({
                    'type': name,
                    'severity': pattern['severity'],
                    'fix': pattern['fix'],
                    'example_wrong': pattern['example_wrong'],
                    'example_right': pattern['example_right']
                })
        
        return errors


class ConversionService:
    """Service for converting COBOL code using Databricks Foundation Models"""
    
    def __init__(self, token, endpoint, model, instructions):
        # Validate token
        if not token or token == "None":
            raise ValueError("Invalid authentication token provided")
        
        self.client = OpenAI(api_key=token, base_url=endpoint)
        self.model = model
        self.instructions = instructions
        self.token = token
        self.validator = CodeValidator()  # Regex validator only
    
    def convert_cobol_code(self, cobol_code, output_type, source_catalog, source_schema, target_catalog, target_schema, max_tokens=3000):
        """Convert COBOL code to PySpark or SQL"""
        start_time = time.time()
        
        is_notebook = "Notebook" in output_type
        base_output_type = output_type.replace(" Notebook", "").replace(" (DBSQL)", "")
        if "SQL" in base_output_type:
            base_output_type = "SQL"
        
        try:
            # Build mode-specific instructions
            if base_output_type == "SQL":
                mode_instructions = """
OUTPUT MODE: Pure Databricks SQL (DBSQL)
- Use CREATE OR REPLACE TABLE for all table operations
- Use pure SQL syntax (SELECT, WHERE, GROUP BY, JOIN, CASE WHEN)
- Use CAST() for type conversions
- Use SQL window functions with OVER clause
- NO PySpark DataFrame API (no df.withColumn, no F.when)
"""
            else:
                mode_instructions = """
OUTPUT MODE: PySpark DataFrame API
- Use PySpark DataFrame API for all operations
- Import: from pyspark.sql import functions as F, Window
- Use df.withColumn(), df.filter(), df.groupBy().agg()
- Use F.when(), F.col(), F.lit() for expressions
- NO SQL syntax (no CREATE TABLE, no SELECT statements)
"""
            
            # Build comprehensive system prompt with ALL critical rules
            system_prompt = f"""You are a COBOL to Databricks converter for healthcare payer systems.

{mode_instructions}

=== CRITICAL RULES (NEVER VIOLATE!) ===

RULE 1: ALWAYS import both libraries for PySpark mode
```python
from pyspark.sql import functions as F
from pyspark.sql import Window  # MANDATORY - even if not used!
```

RULE 2: ALWAYS cast aggregations immediately (both modes)
PySpark:
- F.min("col").cast("double")
- F.max("col").cast("double")
- F.avg("col").cast("double")
- F.sum("col").cast("double")
- F.count("*").cast("long")

SQL:
- CAST(MIN(col) AS DOUBLE)
- CAST(MAX(col) AS DOUBLE)
- CAST(AVG(col) AS DOUBLE)
- CAST(SUM(col) AS DOUBLE)
- CAST(COUNT(*) AS LONG)

RULE 3: ALWAYS use overwriteSchema for PySpark table writes
```python
df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("catalog.schema.table")
```
NOT: df.write.mode("overwrite").saveAsTable(...)  # MISSING overwriteSchema!

RULE 4: ALWAYS use 3-level namespace
- Source reads: {source_catalog}.{source_schema}.table_name
- Target writes: {target_catalog}.{target_schema}.table_name
NOT: Just "table_name" or "schema.table_name"

RULE 5: ALWAYS check for division by zero
PySpark:
```python
F.when(F.col("denominator") > 0, F.col("numerator") / F.col("denominator")).otherwise(None)
```
SQL:
```sql
CASE WHEN denominator > 0 THEN numerator / denominator ELSE NULL END
```

RULE 6: ALWAYS cast date columns before operations (if not already DATE type)
PySpark:
```python
F.col("date_str").cast("date")
```
SQL:
```sql
CAST(date_str AS DATE)
```

RULE 7: ALWAYS use explicit ORDER BY if output order matters
PySpark:
```python
df.orderBy(F.col("date").desc(), F.col("id"))
```
SQL:
```sql
ORDER BY date DESC, id ASC
```

RULE 8: ALWAYS handle NULLs in joins and filters
PySpark:
```python
df.filter(F.col("col").isNotNull() & (F.col("col") != ""))
```
SQL:
```sql
WHERE col IS NOT NULL AND col != ''
```

RULE 9: ALWAYS use Window.partitionBy with logical grouping key
PySpark:
```python
window_spec = Window.partitionBy("member_id").orderBy(F.col("date").desc())
df.withColumn("row_num", F.row_number().over(window_spec))
```

RULE 10: NEVER use SELECT *, col_name in SQL mode
This causes COLUMN_ALREADY_EXISTS errors if col_name already exists!
Use SELECT * REPLACE (col_expr AS col_name) or list columns explicitly.

=== PATTERN RECOGNITION CHECKLIST ===
When converting SAS code, ALWAYS check for these patterns:

✅ ANY division → Add zero check
✅ ANY aggregation → Add .cast("double") or .cast("long")
✅ ANY table write → Add .option("overwriteSchema", "true")
✅ ANY window function → Import Window, use partitionBy
✅ ANY date operation → Cast to date if needed
✅ ANY NULL-sensitive logic → Add explicit NULL checks
✅ ANY join → Cast IDs to same type on both sides
✅ ANY ORDER BY needed → Add explicit .orderBy() or ORDER BY
✅ ANY string operation → Check for NULL/empty strings first

=== FULL INSTRUCTIONS FROM FILE ===
{self.instructions}

=== CONVERSION REQUIREMENTS ===
- Generate production-ready, runnable code
- Include all necessary imports
- Add comments for complex business logic
- Handle edge cases (NULLs, zeros, empty strings)
- Use healthcare payer naming conventions
- Follow Databricks best practices
"""
            
            user_prompt = f"""Convert this COBOL mainframe code to {base_output_type}.

ENVIRONMENT:
- Source catalog: {source_catalog}
- Source schema: {source_schema}
- Target catalog: {target_catalog}
- Target schema: {target_schema}

CRITICAL REMINDERS:
1. PySpark mode: MUST use .option("overwriteSchema", "true") on ALL writes
2. MUST cast ALL aggregations: .cast("double") or .cast("long")
3. MUST import both F and Window for PySpark mode
4. MUST use 3-level namespace for all table references
5. MUST add division-by-zero checks

COBOL CODE TO CONVERT:
{cobol_code}

Generate complete, production-ready {base_output_type} code following ALL rules above!"""
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.model,
                max_tokens=max_tokens,
                timeout=120
            )
            
            converted_code = response.choices[0].message.content
            
            return {
                "success": True,
                "converted_code": converted_code,
                "error": None,
                "execution_time": time.time() - start_time,
                "model_used": self.model,
                "is_notebook": is_notebook,
                "base_output_type": base_output_type,
                "source_catalog": source_catalog,
                "source_schema": source_schema,
                "target_catalog": target_catalog,
                "target_schema": target_schema
            }
        except Exception as e:
            return {
                "success": False,
                "converted_code": None,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "model_used": self.model
            }

def generate_databricks_notebook_content(code, output_type, source_catalog, source_schema, target_catalog, target_schema, original_filename):
    """Generate Databricks notebook with parameters - Python with spark.sql() for Hybrid, Python for PySpark"""
    
    if output_type == "SQL" or output_type == "Hybrid":
        # Hybrid mode - Python notebook with spark.sql() for reads + df.withColumn() for transforms
        notebook_content = f"""# Databricks notebook source
# MAGIC %md
# MAGIC # {original_filename.replace('.cbl', '').replace('.cobol', '').replace('.cob', '')} - Converted from COBOL
# MAGIC 
# MAGIC **Original File**: `{original_filename}`  
# MAGIC **Converted**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
# MAGIC **Output Type**: Pure Databricks SQL
# MAGIC 
# MAGIC ---
# MAGIC 
# MAGIC ##    IMPORTANT: About COLUMN_ALREADY_EXISTS Errors
# MAGIC 
# MAGIC ### What is this error?
# MAGIC If you see `[COLUMN_ALREADY_EXISTS] The column 'column_name' already exists`, this SQL contains:
# MAGIC ```sql
# MAGIC SELECT *, CASE WHEN ... AS column_name FROM table
# MAGIC ```
# MAGIC where `column_name` already exists in the source table.
# MAGIC 
# MAGIC ### Why?
# MAGIC - `SELECT *` brings ALL existing columns
# MAGIC - Then you try to add a column with the same name --> Duplicate!
# MAGIC 
# MAGIC ### How to fix (4 options):
# MAGIC 
# MAGIC **Option 1: Use `SELECT * REPLACE` (Recommended)**
# MAGIC ```sql
# MAGIC --  GOOD: Replaces existing column
# MAGIC SELECT * REPLACE (CASE WHEN status IS NULL THEN 'PENDING' ELSE status END AS status)
# MAGIC FROM table
# MAGIC ```
# MAGIC 
# MAGIC **Option 2: Use different column name**
# MAGIC ```sql
# MAGIC --  Creates new column
# MAGIC SELECT *, CASE WHEN status IS NULL THEN 'PENDING' ELSE status END AS status_clean
# MAGIC FROM table
# MAGIC ```
# MAGIC 
# MAGIC **Option 3: List columns explicitly**
# MAGIC ```sql
# MAGIC --  Explicit (verbose but safe)
# MAGIC SELECT id, CASE WHEN status IS NULL THEN 'PENDING' ELSE status END AS status, amount FROM table
# MAGIC ```
# MAGIC 
# MAGIC **Option 4: Convert to PySpark**
# MAGIC ```python
# MAGIC from pyspark.sql import functions as F
# MAGIC df = spark.table(f"{source_catalog}.{source_schema}.table")
# MAGIC df = df.withColumn("status", F.when(F.col("status").isNull(), F.lit("PENDING")).otherwise(F.col("status")))
# MAGIC # PySpark auto-overwrites duplicates - no error!
# MAGIC ```
# MAGIC 
# MAGIC ---
# MAGIC 
# MAGIC ##   Configurable Parameters
# MAGIC Use the widgets below to configure catalog and schema settings at runtime

# COMMAND ----------

# MAGIC %md
# MAGIC ### Configuration Widgets

# COMMAND ----------

# MAGIC %python

# Create widgets for runtime configuration
dbutils.widgets.text("source_catalog", "{source_catalog}", "Source Catalog")
dbutils.widgets.text("source_schema", "{source_schema}", "Source Schema")
dbutils.widgets.text("target_catalog", "{target_catalog}", "Target Catalog")
dbutils.widgets.text("target_schema", "{target_schema}", "Target Schema")

# Get widget values as Python variables
source_catalog = dbutils.widgets.get("source_catalog")
source_schema = dbutils.widgets.get("source_schema")
target_catalog = dbutils.widgets.get("target_catalog")
target_schema = dbutils.widgets.get("target_schema")

print(f"  Reading from: {{source_catalog}}.{{source_schema}}")
print(f"    Writing to: {{target_catalog}}.{{target_schema}}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Converted SQL Code

# COMMAND ----------

# MAGIC %sql

{code}
"""
    else:
        # PySpark notebook - use Python language with explicit %python magic
        notebook_content = f"""# Databricks notebook source
# MAGIC %md
# MAGIC # {original_filename.replace('.cbl', '').replace('.cobol', '').replace('.cob', '')} - Converted from COBOL
# MAGIC 
# MAGIC **Original File**: `{original_filename}`  
# MAGIC **Converted**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
# MAGIC **Output Type**: PySpark
# MAGIC 
# MAGIC ---
# MAGIC 
# MAGIC ##   Configurable Parameters
# MAGIC Use the widgets below to configure catalog and schema settings at runtime

# COMMAND ----------

# MAGIC %md
# MAGIC ### Configuration Widgets

# COMMAND ----------

# MAGIC %python

# Create widgets for runtime configuration
dbutils.widgets.text("source_catalog", "{source_catalog}", "Source Catalog")
dbutils.widgets.text("source_schema", "{source_schema}", "Source Schema")
dbutils.widgets.text("target_catalog", "{target_catalog}", "Target Catalog")
dbutils.widgets.text("target_schema", "{target_schema}", "Target Schema")

# Get widget values
source_catalog = dbutils.widgets.get("source_catalog")
source_schema = dbutils.widgets.get("source_schema")
target_catalog = dbutils.widgets.get("target_catalog")
target_schema = dbutils.widgets.get("target_schema")

print(f"  Reading from: {{source_catalog}}.{{source_schema}}")
print(f"    Writing to: {{target_catalog}}.{{target_schema}}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Converted Code

# COMMAND ----------

# MAGIC %python

{code}
"""
    
    return notebook_content


def generate_conversion_summary(results, saved_files, output_dir):
    """Generate markdown summary of conversion session"""
    summary = f"""# COBOL to Databricks Conversion Summary

**Date**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Location**: `{output_dir}`
**Model**: {MODEL_NAME}

---

## Files Converted

"""
    
    for result in results:
        status = " Success" if result['success'] else " Failed"
        exec_time = result.get('execution_time', 0)
        exec_time_formatted = f"{exec_time:.2f}"
        summary += f"\n### {result['filename']}\n"
        summary += f"- **Status**: {status}\n"
        summary += f"- **Output Type**: {result.get('output_type', 'N/A')}\n"
        summary += f"- **Execution Time**: {exec_time_formatted}s\n"
        
        if result['success']:
            is_notebook = result.get('is_notebook', False)
            base_output_type = result.get('base_output_type', result.get('output_type', 'PySpark'))
            
            if is_notebook:
                extension = ""  # Databricks notebooks have no extension
                output_name = result['filename'].replace('.cbl', f'_converted{extension}').replace('.cobol', f'_converted{extension}').replace('.cob', f'_converted{extension}')
                summary += f"- **Output File**: `{output_name}` (Databricks Notebook)\n"
            else:
                extension = ".py" if base_output_type == "PySpark" else ".sql"
                output_name = result['filename'].replace('.cbl', f'_converted{extension}').replace('.cobol', f'_converted{extension}').replace('.cob', f'_converted{extension}')
                summary += f"- **Output File**: `{output_name}`\n"
            
            summary += f"- **Source**: `{result.get('source_catalog', 'N/A')}.{result.get('source_schema', 'N/A')}`\n"
            summary += f"- **Target**: `{result.get('target_catalog', 'N/A')}.{result.get('target_schema', 'N/A')}`\n"
        else:
            summary += f"- **Error**: {result.get('error', 'Unknown')}\n"
    
    # Calculate stats outside f-string to avoid format spec issues
    total_files = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = sum(1 for r in results if not r['success'])
    success_rate = (successful / total_files * 100) if total_files > 0 else 0
    success_rate_formatted = f"{success_rate:.1f}"
    
    summary += f"""

---

## Statistics

- **Total Files**: {total_files}
- **Successful**: {successful}
- **Failed**: {failed}
- **Success Rate**: {success_rate_formatted}%

---

## Next Steps

1. Review converted files in this folder
2. Test converted code in Databricks notebooks
3. Update any hardcoded values or paths
4. Run data validation checks
5. Deploy to production workflow

---

*Generated by COBOL to Databricks Converter App*
"""
    
    return summary


def main():
    """Main application logic"""
    
    # Header
    st.markdown('<h1 class="main-header">💼  COBOL to Databricks Converter</h1>', unsafe_allow_html=True)
    
    # Show user info if available
    user_display = username if username != "app-user" else "Databricks App"
    st.markdown(
        f'<p class="sub-header">Powered by Databricks Foundation Models (Claude Sonnet 4.5) | Convert Mainframe COBOL to Modern PySpark/SQL</p>',
        unsafe_allow_html=True
    )
    
    # Load assistant instructions from app bundle
    assistant_instructions = load_instructions()
    
    # Initialize conversion service
    if databricks_token is None:
        st.error(" Could not retrieve authentication token. Please contact administrator.")
        st.stop()
    
    service = ConversionService(
        token=databricks_token,
        endpoint=SERVING_ENDPOINT,
        model=MODEL_NAME,
        instructions=assistant_instructions
    )
    
    # Sidebar - File Input and Settings
    with st.sidebar:
        st.header("  File Input")
        
        # Source selection tabs
        # Note: Workspace tab commented out - can be re-enabled later if needed
        source_tab1, source_tab3 = st.tabs(["  Local", "   Volume"])
        
        ### TAB 1: Local Upload ###
        with source_tab1:
            st.caption("Upload COBOL files (.cbl, .cob, .cobol) from your computer")
            
            uploaded_files = st.file_uploader(
                "Choose COBOL files",
                type=['cbl', 'cob', 'cobol', 'txt'],
                accept_multiple_files=True,
                help="Maximum file size: 5MB per file"
            )
            
            if uploaded_files:
                st.session_state.cobol_files = []
                for file in uploaded_files:
                    content = file.getvalue().decode('utf-8')
                    st.session_state.cobol_files.append({
                        'filename': file.name,
                        'content': content,
                        'source': 'local',
                        'size': file.size
                    })
                st.success(f" Loaded {len(uploaded_files)} file(s)")
        
        ### TAB 2: Workspace Files - COMMENTED OUT (can be re-enabled later) ###
        # with source_tab2:
        #     st.caption("Select files from Databricks workspace")
        #     
        #     workspace_path = st.text_input(
        #         "Workspace path",
        #         value=f"/Workspace/Users/{username}/",
        #         help="Enter the workspace folder path containing SAS files"
        #     )
        #     
        #     if st.button("  Browse", key="browse_workspace"):
        #         try:
        #             # List files using workspace API
        #             files = w.workspace.list(workspace_path)
        #             sas_files = [f for f in files if f.path.endswith('.sas')]
        #             
        #             if sas_files:
        #                 selected_files = st.multiselect(
        #                     f"Select SAS files ({len(sas_files)} found)",
        #                     options=[f.path.split('/')[-1] for f in sas_files]
        #                 )
        #                 
        #                 if st.button(" Load Selected", key="load_workspace"):
        #                     st.session_state.sas_files = []
        #                     for filename in selected_files:
        #                         file_path = workspace_path.rstrip('/') + '/' + filename
        #                         # Download file content
        #                         content_bytes = w.workspace.download(file_path).contents.read()
        #                         content = content_bytes.decode('utf-8')
        #                         st.session_state.sas_files.append({
        #                             'filename': filename,
        #                             'content': content,
        #                             'source': 'workspace',
        #                             'path': file_path
        #                         })
        #                     st.success(f" Loaded {len(selected_files)} file(s)")
        #                     st.rerun()
        #             else:
        #                 st.warning("No .sas files found in this path")
        #         except Exception as e:
        #             st.error(f" Error: {e}")
        
        ### TAB 3: Volume Files ###
        with source_tab3:
            st.caption("Select files from Unity Catalog volumes")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                catalog = st.text_input("Catalog", value=os.getenv('SOURCE_CATALOG', 'payer_dev'), key="vol_catalog")
            with col2:
                schema = st.text_input("Schema", value=os.getenv('VOLUME_SCHEMA', 'cobol_migration'), key="vol_schema")
            with col3:
                volume = st.text_input("Volume", value=os.getenv('VOLUME_NAME', 'legacy_cobol'), key="vol_volume")
            
            subdirectory = st.text_input(
                "Subdirectory (optional)",
                value="",
                placeholder="e.g., hedis/2024",
                help="Leave empty to browse root of volume"
            )
            
            if subdirectory:
                volume_path = f"/Volumes/{catalog}/{schema}/{volume}/{subdirectory}"
            else:
                volume_path = f"/Volumes/{catalog}/{schema}/{volume}"
            
            st.caption(f"Path: `{volume_path}`")
            
            # Initialize session state for volume files
            if 'volume_files' not in st.session_state:
                st.session_state.volume_files = []
            
            if st.button("   Browse", key="browse_volume"):
                try:
                    # List files in volume using Files API
                    files = w.files.list_directory_contents(volume_path)
                    cobol_files = [f for f in files if f.path.endswith(('.cbl', '.cobol', '.cob'))]
                    
                    if cobol_files:
                        # Store files in session state
                        st.session_state.volume_files = [f.path.split('/')[-1] for f in cobol_files]
                        st.session_state.volume_path = volume_path
                        st.session_state.volume_catalog = catalog
                        st.session_state.volume_schema = schema
                        st.session_state.volume_name = volume
                    else:
                        st.session_state.volume_files = []
                        st.warning("No COBOL files (.cbl, .cobol, .cob) found in this volume path")
                except Exception as e:
                    st.session_state.volume_files = []
                    st.error(f" Error: {e}")
            
            # Show file selector if files were found (persists across reruns)
            if st.session_state.volume_files:
                selected_files = st.multiselect(
                    f"Select COBOL files ({len(st.session_state.volume_files)} found)",
                    options=st.session_state.volume_files,
                    key="volume_multiselect"
                )
                
                # Add spacing to prevent dropdown overlap
                st.write("")
                st.write("")
                
                if st.button(" Load Selected", key="load_volume", disabled=len(selected_files)==0):
                    st.session_state.cobol_files = []
                    for filename in selected_files:
                        file_path = st.session_state.volume_path.rstrip('/') + '/' + filename
                        try:
                            # Download file content from volume
                            content_bytes = w.files.download(file_path).contents.read()
                            content = content_bytes.decode('utf-8')
                            st.session_state.cobol_files.append({
                                'filename': filename,
                                'content': content,
                                'source': 'volume',
                                'path': file_path,
                                'volume': f"{st.session_state.volume_catalog}.{st.session_state.volume_schema}.{st.session_state.volume_name}"
                            })
                        except Exception as e:
                            st.error(f"Error loading {filename}: {e}")
                    
                    if st.session_state.cobol_files:
                        st.success(f" Loaded {len(selected_files)} file(s)")
                        # Clear volume files after successful load
                        st.session_state.volume_files = []
                        st.rerun()
        
        # Show loaded files summary
        if st.session_state.cobol_files:
            st.divider()
            st.success(f" {len(st.session_state.cobol_files)} file(s) ready")
            
            with st.expander("  Loaded Files"):
                for file in st.session_state.cobol_files:
                    source_icon = {
                        'local': ' ',
                        'workspace': ' ',
                        'volume': '  '
                    }.get(file['source'], ' ')
                    
                    st.write(f"{source_icon} **{file['filename']}**")
                    st.caption(f"Source: {file['source']}")
                    if 'path' in file:
                        st.caption(f"Path: `{file['path']}`")
        
        # Output type selector
        st.divider()
        output_type = st.radio(
            "Output Format",
            ["PySpark Notebook", "SQL Notebook (DBSQL)"],
            help="""
            Choose your preferred code style:
              PySpark Notebook: Pure PySpark DataFrame API (df.withColumn, df.filter, df.groupBy)
              SQL Notebook (DBSQL): Pure Databricks SQL (CREATE TABLE, SELECT, INSERT)
            
               SQL mode may generate SELECT *, patterns that can cause COLUMN_ALREADY_EXISTS errors.
            Each notebook includes instructions on how to fix this if it occurs.
            """
        )
        
        # Catalog and Schema Configuration
        st.divider()
        st.subheader("   Catalog & Schema Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Source (Read From)**")
            source_catalog = st.text_input(
                "Source Catalog",
                value=os.getenv('SOURCE_CATALOG', 'payer_dev'),
                help="Catalog where source data is located"
            )
            source_schema = st.text_input(
                "Source Schema",
                value=os.getenv('SOURCE_SCHEMA', 'analytics_gold'),
                help="Schema with gold tables to read from"
            )
        
        with col2:
            st.markdown("**Target (Write To)**")
            target_catalog = st.text_input(
                "Target Catalog",
                value=os.getenv('TARGET_CATALOG', 'payer_analyst_dev'),
                help="Catalog where converted code will write results"
            )
            target_schema = st.text_input(
                "Target Schema",
                value=os.getenv('TARGET_SCHEMA', 'default'),
                help="Schema where results will be written"
            )
        
        # Show full namespace
        st.caption(f"  **Read from**: `{source_catalog}.{source_schema}.*` -->    **Write to**: `{target_catalog}.{target_schema}.*`")

        
        # Instructions viewer
        st.divider()
        st.subheader("   Conversion Rules")
        
        with st.expander("  View Assistant Instructions"):
            st.markdown("""
            The app uses pre-configured conversion rules that include:
            - Source catalogs and schemas
            - Target catalogs and schemas
            - COBOL to PySpark/SQL mappings (PERFORM, IF-THEN-ELSE, MOVE, COMPUTE)
            - Coding standards
            - Healthcare payer-specific conventions
            """)
            
            if st.checkbox("Show full instructions"):
                st.text_area(
                    "Instructions Content (Read-Only)",
                    value=assistant_instructions,
                    height=300,
                    disabled=True,
                    help="These instructions are configured in the app deployment"
                )
    
    # Main content area
    if not st.session_state.cobol_files:
        st.info("💼  Select or upload COBOL files from the sidebar to get started")
        
        st.markdown("""
        ### How it works:
        
        1. **Load COBOL files** using one of two methods:
           -   Upload from your laptop (.cbl, .cobol, .cob files)
           -    Select from Unity Catalog volumes
        2. **Choose output format**: PySpark or SQL
        3. **Click Convert** to process all files
        4. **Review** the converted code side-by-side
        5. **Save** to a custom folder in your workspace
        
        ### Features:
        -   AI-powered conversion using Claude Sonnet 4.5
        -   Mainframe COBOL to modern Databricks
        -   Batch processing support
        -   Detailed conversion reports
        -   Save to custom workspace folders
        -  Code validation and warnings
        -    Customizable conversion rules
        """)
    
    else:
        # Show file previews
        st.subheader("  Files Ready for Conversion")
        
        for file_data in st.session_state.cobol_files:
            with st.expander(f"  {file_data['filename']} ({estimate_conversion_complexity(file_data['content'])} complexity)"):
                metadata = extract_metadata(file_data['content'])
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Lines", metadata['line_count'])
                with col2:
                    st.metric("PROCs", metadata['proc_count'])
                with col3:
                    st.metric("SQL", "Yes" if metadata['has_sql'] else "No")
                with col4:
                    st.metric("Macros", "Yes" if metadata['has_macro'] else "No")
                
                if metadata['procs_used']:
                    st.write(f"**PROCs used**: {', '.join(metadata['procs_used'])}")
                
                st.code(format_cobol_code_preview(file_data['content'], max_lines=15), language='cobol')
        
        # Convert button
        st.divider()
        
        if st.button("  Convert All Files", type="primary", use_container_width=True):
            st.session_state.conversion_results = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, file_data in enumerate(st.session_state.cobol_files):
                status_text.text(f"Converting {file_data['filename']}... ({i+1}/{len(st.session_state.cobol_files)})")
                
                # Validate file
                is_valid, msg = validate_cobol_file(file_data['content'])
                if not is_valid:
                    st.session_state.conversion_results.append({
                        'filename': file_data['filename'],
                        'success': False,
                        'error': f"Invalid COBOL file: {msg}",
                        'source': file_data['source'],
                        'execution_time': 0
                    })
                    continue
                
                # Convert
                result = service.convert_cobol_code(
                    cobol_code=file_data['content'],
                    output_type=output_type,
                    source_catalog=source_catalog,
                    source_schema=source_schema,
                    target_catalog=target_catalog,
                    target_schema=target_schema,
                    max_tokens=MAX_TOKENS
                )
                
                result['filename'] = file_data['filename']
                result['original_code'] = file_data['content']
                result['output_type'] = output_type
                result['source'] = file_data['source']
                
                if result['success']:
                    result['converted_code'] = extract_code_blocks(result['converted_code'])
                    result['validation'] = validate_conversion(result['converted_code'], output_type)
                
                st.session_state.conversion_results.append(result)
                progress_bar.progress((i + 1) / len(st.session_state.cobol_files))
            
            status_text.text(" Conversion complete!")
            progress_bar.empty()
            
            # Show validation summary
            total_errors_fixed = sum(r.get('errors_found', 0) for r in st.session_state.conversion_results if r['success'])
            if total_errors_fixed > 0:
                st.success(f"  Converted {len(st.session_state.cobol_files)} file(s)!   Auto-corrected {total_errors_fixed} error(s)")
            else:
                st.success(f"  Converted {len(st.session_state.cobol_files)} file(s)!")
    
    # Display results
    if st.session_state.conversion_results:
        st.divider()
        
        # Show validation summary prominently
        total_files = len(st.session_state.conversion_results)
        successful_files = sum(1 for r in st.session_state.conversion_results if r['success'])
        total_errors_found = sum(r.get('errors_found', 0) for r in st.session_state.conversion_results if r['success'])
        
        if total_errors_found > 0:
            st.info(f"""
              **Validation & Auto-Correction Summary**
            - Files processed: {total_files}
            - Successful: {successful_files}
            - Errors auto-corrected: **{total_errors_found}**
            
            *The validation system detected and automatically fixed {total_errors_found} error(s) in your code!*
            """)
        else:
            st.info(f"""
             **Validation Summary**
            - Files processed: {total_files}
            - Successful: {successful_files}
            - Errors found: 0
            
            *All files passed validation checks!*
            """)
        
        st.subheader("  Conversion Results")
        
        # Tabs for different views
        tab1, tab2 = st.tabs(["  Side-by-Side View", "  Summary Report"])
        
        with tab1:
            # File selector
            result_filenames = [r['filename'] for r in st.session_state.conversion_results]
            selected_file = st.selectbox("Select file to view:", result_filenames)
            
            # Find selected result
            selected_result = next(r for r in st.session_state.conversion_results if r['filename'] == selected_file)
            
            if selected_result['success']:
                # Show validation warnings
                if selected_result.get('validation'):
                    val = selected_result['validation']
                    if val['warnings']:
                        st.warning("   **Warnings:**\n" + "\n".join(f"- {w}" for w in val['warnings']))
                    if val['issues']:
                        st.error(" **Issues:**\n" + "\n".join(f"- {i}" for i in val['issues']))
                
                # Show execution time
                exec_time = selected_result['execution_time']
                exec_time_formatted = f"{exec_time:.2f}"
                st.info(f"   Conversion completed in {exec_time_formatted} seconds")
                
                # Side-by-side code display
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**  Original COBOL Code**")
                    st.code(selected_result['original_code'], language='cobol', line_numbers=True)
                
                with col2:
                    base_output_type = selected_result.get('base_output_type', selected_result['output_type'])
                    is_notebook = selected_result.get('is_notebook', False)
                    output_label = f"{selected_result['output_type']} {'Notebook' if is_notebook else 'Code'}"
                    st.markdown(f"**  Converted {output_label}**")
                    
                    # Show config info
                    st.caption(f"  Source: `{selected_result.get('source_catalog', 'N/A')}.{selected_result.get('source_schema', 'N/A')}` -->    Target: `{selected_result.get('target_catalog', 'N/A')}.{selected_result.get('target_schema', 'N/A')}`")
                    
                    # Show full notebook content if it's a notebook (with widgets)
                    if is_notebook:
                        full_notebook_content = generate_databricks_notebook_content(
                            code=selected_result['converted_code'],
                            output_type=base_output_type,
                            source_catalog=selected_result.get('source_catalog', 'payer_dev'),
                            source_schema=selected_result.get('source_schema', 'analytics_gold'),
                            target_catalog=selected_result.get('target_catalog', 'payer_analyst_dev'),
                            target_schema=selected_result.get('target_schema', 'default'),
                            original_filename=selected_result['filename']
                        )
                        st.code(full_notebook_content, language='python', line_numbers=True)
                    else:
                        language = 'python' if 'PySpark' in base_output_type else 'sql'
                        st.code(selected_result['converted_code'], language=language, line_numbers=True)
                
                # Download button for individual file
                st.divider()
                is_notebook = selected_result.get('is_notebook', False)
                base_output_type = selected_result.get('base_output_type', selected_result['output_type'])
                
                if is_notebook:
                    # Databricks notebooks have NO extension
                    extension = ""
                    download_content = generate_databricks_notebook_content(
                        code=selected_result['converted_code'],
                        output_type=base_output_type,
                        source_catalog=selected_result.get('source_catalog', 'payer_dev'),
                        source_schema=selected_result.get('source_schema', 'analytics_gold'),
                        target_catalog=selected_result.get('target_catalog', 'payer_analyst_dev'),
                        target_schema=selected_result.get('target_schema', 'default'),
                        original_filename=selected_result['filename']
                    )
                    mime_type = "text/x-python"
                else:
                    extension = ".py" if base_output_type == "PySpark" else ".sql"
                    download_content = selected_result['converted_code']
                    mime_type = "text/plain"
                
                download_filename = selected_result['filename'].replace('.cbl', f'_converted{extension}').replace('.cobol', f'_converted{extension}').replace('.cob', f'_converted{extension}')
                
                st.download_button(
                    label=f"  Download {download_filename}",
                    data=download_content,
                    file_name=download_filename,
                    mime=mime_type,
                    use_container_width=True
                )
            else:
                st.error(f" Conversion failed: {selected_result['error']}")
        
        with tab2:
            # Generate and display report
            report = generate_report(st.session_state.conversion_results)
            st.markdown(report)
        
        # Save to workspace section
        st.divider()
        st.subheader("  Save to Workspace")
        
        # Extract user prefix for folder naming
        user_prefix = os.getenv('USER_PREFIX', username.split('@')[0].split('.')[0][:3].lower())
        
        # Use a shared location with user-specific parent folder
        parent_folder = f"/Workspace/Shared/cobol_conversions_{user_prefix}"
        
        # Auto-generate folder name with timestamp and user prefix (format: vik_20251127_195345)
        auto_folder_name = f"{user_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Folder name input (read-only display)
        st.text_input(
            "Folder name",
            value=auto_folder_name,
            disabled=True,
            help="Auto-generated folder name with timestamp format: YYYYMMDD_HHMMSS"
        )
        
        folder_name = auto_folder_name
        
        # Save button
        if st.button("  Save All Converted Files", type="primary", use_container_width=True):
            if not folder_name:
                st.error(" Please enter a folder name")
            else:
                # Sanitize folder name
                safe_folder_name = re.sub(r'[^\w\-_]', '_', folder_name)
                output_dir = f"{parent_folder}/{safe_folder_name}"
                
                # Create parent directory first, then child directory using Databricks SDK
                try:
                    w.workspace.mkdirs(parent_folder)
                    w.workspace.mkdirs(output_dir)
                except Exception as e:
                    st.error(f" Could not create folder: {e}")
                    st.stop()
                
                # Save files using Databricks SDK
                saved_files = []
                for result in st.session_state.conversion_results:
                    if result['success']:
                        is_notebook = result.get('is_notebook', False)
                        base_output_type = result.get('base_output_type', result.get('output_type', 'PySpark'))
                        base_name = result['filename'].replace('.cbl', '').replace('.cobol', '').replace('.cob', '')
                        
                        # Determine file extension and content
                        if is_notebook:
                            # Databricks notebooks have NO extension
                            extension = ""
                            # Generate Databricks notebook format
                            file_content = generate_databricks_notebook_content(
                                code=result['converted_code'],
                                output_type=base_output_type,
                                source_catalog=result.get('source_catalog', os.getenv('SOURCE_CATALOG', 'payer_dev')),
                                source_schema=result.get('source_schema', os.getenv('SOURCE_SCHEMA', 'analytics_gold')),
                                target_catalog=result.get('target_catalog', os.getenv('TARGET_CATALOG', 'payer_analyst_dev')),
                                target_schema=result.get('target_schema', os.getenv('TARGET_SCHEMA', 'default')),
                                original_filename=result['filename']
                            )
                        else:
                            extension = ".py" if base_output_type == "PySpark" else ".sql"
                            file_content = result['converted_code']
                        
                        output_filename = f"{base_name}_converted{extension}"
                        output_path = f"{output_dir}/{output_filename}"
                        
                        try:
                            # SQL notebooks use SQL language, PySpark notebooks use Python language
                            # Delete existing file/notebook first
                            try:
                                w.workspace.delete(output_path)
                            except:
                                pass  # Doesn't exist yet
                            
                            # Import notebook with appropriate language
                            from databricks.sdk.service.workspace import ImportFormat, Language
                            import base64
                            
                            # Both output types use Python language now (SQL uses spark.sql())
                            notebook_language = Language.PYTHON
                            
                            # Base64 encode the content (required by workspace.import_ API)
                            content_bytes = file_content.encode('utf-8')
                            content_b64 = base64.b64encode(content_bytes).decode('utf-8')
                            
                            w.workspace.import_(
                                path=output_path,
                                format=ImportFormat.SOURCE,
                                language=notebook_language,
                                content=content_b64,
                                overwrite=False
                            )
                            
                            saved_files.append(output_filename)
                        except Exception as e:
                            st.error(f" Error saving {output_filename}: {str(e)[:300]}")
                
                # Create summary file
                if saved_files:
                    try:
                        summary = generate_conversion_summary(
                            st.session_state.conversion_results,
                            saved_files,
                            output_dir
                        )
                        summary_path = f"{output_dir}/CONVERSION_SUMMARY.md"
                        w.workspace.upload(
                            path=summary_path,
                            content=summary.encode('utf-8'),
                            format=ImportFormat.AUTO,
                            overwrite=True
                        )
                        saved_files.append("CONVERSION_SUMMARY.md")
                    except Exception as e:
                        # Non-critical - just log warning
                        st.warning(f"   Summary file not created: {str(e)[:100]}")
                    
                    # Success message
                    st.success(f" Saved {len(saved_files)} file(s) to workspace!")
                    
                    st.info(f"""
  **Location:** `/Workspace/Shared/cobol_conversions_{user_prefix}/{safe_folder_name}/`

**Files saved:**
{chr(10).join(f'- {f}' for f in saved_files)}

**To access your files:**
1. Click "Workspace" in the left sidebar
2. Navigate to "Shared" folder
3. Open: `cobol_conversions_{user_prefix}/{safe_folder_name}`
""")


if __name__ == "__main__":
    main()

