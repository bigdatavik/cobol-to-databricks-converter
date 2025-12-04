"""
Utility functions for the Streamlit app
"""

import zipfile
from io import BytesIO
from typing import List, Dict
from pygments import highlight
from pygments.lexers import PythonLexer, SqlLexer
from pygments.formatters import HtmlFormatter


def calculate_stats(results: List[Dict]) -> Dict:
    """
    Calculate conversion statistics from results.
    
    Args:
        results: List of conversion result dictionaries
    
    Returns:
        dict with statistics
    """
    total = len(results)
    if total == 0:
        return {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0
        }
    
    successful = sum(1 for r in results if r['success'])
    failed = total - successful
    avg_time = sum(r['execution_time'] for r in results) / total
    
    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "success_rate": (successful / total * 100) if total > 0 else 0,
        "avg_execution_time": avg_time
    }


def generate_report(results: List[Dict]) -> str:
    """
    Generate a markdown conversion summary report.
    
    Args:
        results: List of conversion result dictionaries
    
    Returns:
        str: Markdown-formatted report
    """
    stats = calculate_stats(results)
    
    report = f"""## 📊 Conversion Summary

**Overall Statistics:**
- **Total Files**: {stats['total']}
- **Successful**: ✅ {stats['successful']}
- **Failed**: ❌ {stats['failed']}
- **Success Rate**: {stats['success_rate']:.1f}%
- **Average Time**: {stats['avg_execution_time']:.2f}s per file

---

### 📋 Individual Results

"""
    
    for i, result in enumerate(results, 1):
        status_icon = "✅" if result['success'] else "❌"
        status_text = "Success" if result['success'] else "Failed"
        filename = result.get('filename', f'File {i}')
        
        report += f"\n**{i}. {filename}**\n"
        report += f"- Status: {status_icon} {status_text}\n"
        report += f"- Execution Time: {result['execution_time']:.2f}s\n"
        
        # Show validation status if available
        if result['success'] and 'validation_status' in result:
            validation_status = result['validation_status']
            errors_found = result.get('errors_found', 0)
            
            if errors_found > 0:
                report += f"- 🔧 **Validation**: {validation_status}\n"
            else:
                report += f"- ✔️ Validation: {validation_status}\n"
        
        if not result['success']:
            error_msg = result.get('error', 'Unknown error')
            report += f"- Error: `{error_msg}`\n"
        
        report += "\n"
    
    return report


def create_zip(files: List[Dict]) -> BytesIO:
    """
    Create a ZIP file containing all converted files.
    
    Args:
        files: List of dicts with 'filename' and 'content' keys
    
    Returns:
        BytesIO: In-memory ZIP file
    """
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_data in files:
            zip_file.writestr(file_data['filename'], file_data['content'])
    
    zip_buffer.seek(0)
    return zip_buffer


def format_code_with_syntax(code: str, language: str) -> str:
    """
    Format code with syntax highlighting for HTML display.
    
    Args:
        code: Code content
        language: Either "python" or "sql"
    
    Returns:
        str: HTML-formatted code with syntax highlighting
    """
    try:
        lexer = PythonLexer() if language.lower() == "python" else SqlLexer()
        formatter = HtmlFormatter(style='monokai', noclasses=True)
        return highlight(code, lexer, formatter)
    except Exception:
        # Fallback to plain text if highlighting fails
        return f"<pre>{code}</pre>"


def extract_code_blocks(text: str) -> str:
    """
    Extract code blocks from LLM response that might include markdown formatting.
    
    Args:
        text: Response text that might contain ```python or ```sql blocks
    
    Returns:
        str: Extracted code without markdown formatting
    """
    import re
    
    # Remove markdown code blocks with language identifiers
    # Pattern 1: ```python\n...\n```
    # Pattern 2: ```sql\n...\n```
    # Pattern 3: ```\n...\n```
    pattern = r'```(?:python|sql|py|pyspark)?\n?(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if matches:
        # Return the first code block found, stripped of extra whitespace
        code = matches[0].strip()
        # Remove any remaining backticks
        code = code.replace('```', '')
        return code
    
    # If no code blocks found, clean up any stray backticks
    cleaned = text.strip()
    cleaned = re.sub(r'^```(?:python|sql|py|pyspark)?$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
    cleaned = re.sub(r'^```$', '', cleaned, flags=re.MULTILINE)
    
    return cleaned.strip()


def validate_conversion(converted_code: str, output_type: str) -> Dict:
    """
    Validate converted code for common issues and detect problematic patterns.
    
    Args:
        converted_code: The converted code
        output_type: Either "PySpark" or "SQL"
    
    Returns:
        dict with validation results
    """
    import re
    
    issues = []
    warnings = []
    auto_corrections = []
    
    # Check for 3-level namespace
    if "payer_dev.analytics_gold" not in converted_code:
        warnings.append("Missing 3-level namespace (payer_dev.analytics_gold)")
    
    # Check for target catalog
    if output_type == "PySpark":
        if "payer_analyst_dev" not in converted_code:
            warnings.append("Missing target catalog (payer_analyst_dev)")
        
        # Check for basic PySpark patterns
        if "spark." not in converted_code and "df." not in converted_code:
            issues.append("Does not appear to contain PySpark code")
    
    elif output_type == "SQL":
        # SQL mode uses TRUE HYBRID - check for proper mix
        if "from pyspark.sql import functions as F" not in converted_code:
            warnings.append("SQL hybrid mode should include 'from pyspark.sql import functions as F' for transformations")
        
        # 🔥 CRITICAL: Block DANGEROUS SELECT *, comma pattern (with new columns after comma)
        # This is OK: SELECT * FROM table WHERE condition
        # This is BAD: SELECT *, CASE WHEN ... AS new_col FROM table
        select_star_comma = r'SELECT\s+\*\s*,\s*\w+'
        if re.search(select_star_comma, converted_code, re.IGNORECASE | re.MULTILINE):
            issues.append(
                "❌ BLOCKER: Contains 'SELECT *, <new_columns>' pattern which causes COLUMN_ALREADY_EXISTS errors. "
                "Use df.withColumn() for adding columns, not SELECT *, col pattern."
            )
            auto_corrections.append("Detected SELECT *, col pattern - Use df.withColumn() for hybrid approach")
        
        # Check for CREATE (TABLE or TEMP VIEW) with SELECT *, <new columns>
        # Allow: CREATE TEMP VIEW AS SELECT * FROM table (no new columns)
        # Block: CREATE TEMP VIEW AS SELECT *, new_col FROM table
        create_select_star_comma = r'CREATE\s+(OR\s+REPLACE\s+)?(TEMP\s+VIEW|TABLE)[^;]*?SELECT\s+\*\s*,\s*\w+'
        if re.search(create_select_star_comma, converted_code, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            issues.append(
                "❌ BLOCKER: CREATE TABLE/VIEW with 'SELECT *, <new_columns>' detected. "
                "TRUE hybrid mode: Use spark.sql() for simple SELECT, but df.withColumn() for adding columns."
            )
            auto_corrections.append("CREATE with SELECT *, col detected - Use df.withColumn() after SELECT in hybrid mode")
    
    # Check if code is too short (might be incomplete)
    if len(converted_code) < 50:
        warnings.append("Converted code is very short - might be incomplete")
    
    is_valid = len(issues) == 0
    
    return {
        "is_valid": is_valid,
        "issues": issues,
        "warnings": warnings,
        "auto_corrections": auto_corrections
    }


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        str: Formatted size (e.g., "1.5 KB", "2.3 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

