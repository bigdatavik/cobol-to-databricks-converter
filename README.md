# COBOL to Databricks Converter

A production-ready Streamlit application that converts legacy COBOL mainframe code to PySpark or Databricks SQL using Databricks Foundation Models (Claude Sonnet 4.5).

![Version](https://img.shields.io/badge/version-2.4-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![Databricks](https://img.shields.io/badge/databricks-apps-orange)

---

## Features

- **Multi-format Output**: Generate PySpark DataFrame API or pure Databricks SQL
- **Smart Conversion**: 12 production-validated rules prevent common migration errors
- **Interactive UI**: Streamlit-based interface with real-time previews
- **Foundation Models**: Powered by Claude Sonnet 4.5 for optimal conversion quality
- **Healthcare Focused**: Optimized for healthcare payer analytics (HEDIS, risk adjustment, claims)
- **Production Ready**: Includes comprehensive instructions for LLM (1,700+ lines)

---

## Quick Start

### Prerequisites

- **Databricks workspace** with Unity Catalog enabled
- **Databricks CLI** installed and configured ([Installation Guide](https://docs.databricks.com/en/dev-tools/cli/install.html))
- **Python 3.10+** (for local development only)
- **Workspace permissions**: Ability to create catalogs, schemas, and volumes

### Two Ways to Use This Framework

---

## 🚀 Option 1: Streamlit App (Recommended)

**Best for:** Automated bulk conversions with a user-friendly UI

### Step-by-Step Setup

**1️⃣ Clone the Repository**
```bash
git clone https://github.com/bigdatavik/cobol-to-databricks-converter.git
cd cobol_converter
```

**2️⃣ Configure Databricks CLI**
```bash
# If not already configured
databricks configure

# Or set your profile (optional)
export DATABRICKS_PROFILE="your_profile_name"
```

**3️⃣ Run Full Setup (First Time Only)**

This creates demo catalogs, data, volume, and uploads COBOL files:
```bash
./setup_databricks_assistant.sh
```
**Time:** ~10 minutes | **Creates:** 2 catalogs (vikcbl_payer_dev, vikcbl_payer_analyst_dev), 42K rows of data, 6 COBOL files

**4️⃣ Deploy the Streamlit App**
```bash
./deploy_streamlit_app.sh
```
**Time:** ~30 seconds | **Deploys:** Streamlit app to Databricks Apps

The script will show you a **big reminder box** at the end:

```
╔════════════════════════════════════════════════════════════════╗
║  ⚠️  ACTION REQUIRED: Grant App Permissions (One-Time)         ║
╚════════════════════════════════════════════════════════════════╝
```

**5️⃣ Grant App Permissions (One-Time)**

The deploy script outputs SQL commands. Copy them to **Databricks SQL Editor** and run:

```sql
GRANT USE CATALOG ON CATALOG vikcbl_payer_dev TO `<auto-detected-uuid>`;
GRANT USE SCHEMA ON SCHEMA vikcbl_payer_dev.cobol_migration TO `<auto-detected-uuid>`;
GRANT READ VOLUME ON VOLUME vikcbl_payer_dev.cobol_migration.legacy_cobol TO `<auto-detected-uuid>`;
GRANT SELECT ON CATALOG vikcbl_payer_dev TO `<auto-detected-uuid>`;
GRANT USE CATALOG ON CATALOG vikcbl_payer_analyst_dev TO `<auto-detected-uuid>`;
GRANT SELECT ON CATALOG vikcbl_payer_analyst_dev TO `<auto-detected-uuid>`;
```

**💡 Tip:** Run `./show_grant_commands.sh` anytime to regenerate these commands with your app's UUID.

**6️⃣ Access Your App**

Open the app URL shown in the deploy output:
```
https://vikcbl-cobol-converter-<workspace-id>.azuredatabricksapps.com
```

**✅ You're Done!** Start converting COBOL code to PySpark/SQL.

---

### 🔄 Quick Updates (After Initial Setup)

Already deployed? Just need to update the app or instructions?

```bash
# Update app + instructions only (no data reload)
./deploy_streamlit_app.sh  # ~30 seconds
```

---

## 📝 Option 2: Databricks Assistant (Manual Conversion)

**Best for:** Interactive conversions directly in notebooks with AI assistance

### Setup

Run the same setup script as Option 1:
```bash
./setup_databricks_assistant.sh
```

This deploys `.assistant_instructions.md` to your workspace at:
```
/Workspace/Users/your.email/.assistant_instructions.md
```

### Usage

1. Open any Databricks notebook
2. Click the **Assistant** icon
3. Paste your COBOL code
4. Ask: *"Convert this COBOL to PySpark"*
5. Assistant uses your custom instructions automatically

**Benefits:**
- Context-aware conversions based on your patterns
- Interactive Q&A about COBOL → PySpark/SQL
- Works across all notebooks in your workspace

[Learn more about custom instructions](https://docs.databricks.com/en/notebooks/assistant-tips.html#customize-assistant-responses)

### Local Development

```bash
# Install dependencies
pip install -r dashboard/requirements.txt

# Run locally
cd dashboard
streamlit run cobol_converter_app.py
```

---

## Project Structure

```
cobol_converter/
├── dashboard/                           # Main application
│   ├── cobol_converter_app.py          # Entry point (1,350+ lines)
│   ├── file_handler.py                 # File I/O utilities
│   ├── utils.py                        # Validation & formatting
│   ├── app.yaml                        # Databricks app config
│   └── config/
│       └── .assistant_instructions.md  # LLM instructions (1,800+ lines)
│
├── config/
│   └── .assistant_instructions.md      # Source of truth (edit here!)
│
├── notebooks/                          # Demo notebooks
│   ├── 00c_setup_cobol_demo.py        # Setup script with data generation
│   ├── 01_cobol_hedis_pyspark.py      # HEDIS demo
│   ├── 02_cobol_claims_pyspark.py     # Claims demo
│   ├── 03_cobol_member_sql.py         # Member demo
│   ├── 04_cobol_risk_pyspark.py       # Risk adjustment demo
│   ├── 05_cobol_provider_sql.py       # Provider demo
│   └── README.md
│
├── legacy_cobol/                       # Sample COBOL files
│   ├── hedis_reports.cbl
│   ├── claims_analytics.cbl
│   ├── member_analytics.cbl
│   ├── risk_adjustment.cbl
│   ├── provider_analytics.cbl
│   └── prior_auth_analytics.cbl
│
├── databricks.yml                      # Databricks Asset Bundle config
├── setup_databricks_assistant.sh      # Full setup: catalogs + data + app
└── deploy_streamlit_app.sh            # Quick deploy: app only

```

### Which Approach Should You Use?

**Use the Streamlit App when:**
- You want a self-service UI for business users
- You need batch conversions of multiple COBOL files
- You want consistent, automated output
- You're demoing to customers or stakeholders

**Use Databricks Assistant when:**
- You're actively developing in notebooks
- You want AI help while coding (iterative approach)
- You need to ask questions about COBOL patterns
- You prefer manual control over each conversion step

**Use both!** Many teams deploy the Streamlit app for business users while developers use Databricks Assistant for hands-on work.

---

## Key Features

### 1. Intelligent Code Conversion

The converter follows 12 critical rules validated over 3 days of production testing:

- Always cast aggregations (`.cast("double")` / `.cast("long")`)
- Always use `overwriteSchema=true` on table writes
- Always import both `F` and `Window` for PySpark
- Never use `SELECT *, col` pattern (causes `COLUMN_ALREADY_EXISTS` errors)
- Always check for division by zero
- Always use 3-level namespace (`catalog.schema.table`)
- Plus 6 more...

### 2. Two Output Modes

**PySpark Mode:**
- Pure DataFrame API
- Best for complex transformations
- Auto-overwrites duplicate columns

**SQL Mode:**
- Pure Databricks SQL
- Familiar syntax for SQL users
- Includes warnings about common pitfalls

### 3. Foundation Model Integration

Uses Claude Sonnet 4.5 configured in `dashboard/app.yaml`:

```yaml
- databricks-claude-sonnet-4-5         # Best quality for COBOL conversions
```

### 4. Databricks Assistant Integration

This framework includes comprehensive custom instructions for [Databricks Assistant](https://www.databricks.com/blog/customizing-databricks-assistant-instructions):

**Setup:**
```bash
./setup_databricks_assistant.sh
```

This deploys `.assistant_instructions.md` to your workspace folder (`/Workspace/Users/your.email/.assistant_instructions.md`).

**Usage in Notebooks:**
1. Open any Databricks notebook
2. Use Databricks Assistant (AI helper)
3. Paste your COBOL code and ask: "Convert this COBOL to PySpark"
4. Assistant uses your custom instructions automatically

**Benefits:**
- Context-aware conversions based on your COBOL patterns
- Interactive Q&A about COBOL → PySpark/SQL
- Handles COBOL-specific constructs (REDEFINES, OCCURS, COMP-3, etc.)
- Works across all notebooks in your workspace

[Learn more about custom instructions](https://docs.databricks.com/aws/en/notebooks/assistant-tips#customize-assistant-responses-by-adding-instructions)

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and data flow
- **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** - Demo walkthrough
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Detailed deployment instructions
- **[AUTOMATED_TESTING_GUIDE.md](AUTOMATED_TESTING_GUIDE.md)** - Testing procedures

---

## Usage Example

1. **Upload COBOL File**: Click "Browse files" or paste COBOL code
2. **Configure**: Set source/target catalogs and schemas (defaults to vikcbl_payer_dev)
3. **Select Mode**: Choose PySpark or SQL output
4. **Convert**: Click "Convert to Databricks"
5. **Download**: Save as `.py` notebook file
6. **Deploy**: Upload to Databricks workspace

---

## File Update Workflow

**Critical:** Always edit the source file, then deploy!

```bash
# 1. Edit source
vim config/.assistant_instructions.md

# 2a. Deploy to Streamlit app (auto-syncs to dashboard/config/)
./deploy_streamlit_app.sh

# OR 

# 2b. Deploy to workspace for Databricks Assistant
./setup_databricks_assistant.sh

# Done! Instructions deployed
```

---

## Production Deployment

### Via Script (Recommended)

Choose based on your use case:

```bash
# Option 1: Deploy Streamlit App (~30 seconds)
./deploy_streamlit_app.sh
# Use for: Automated UI-based conversions

# Option 2: Setup Databricks Assistant (~10 minutes)
./setup_databricks_assistant.sh
# Use for: Manual notebook conversions with AI Assistant
```

### ⚠️ Important: Grant App Permissions (One-Time Step)

After deploying the Streamlit app, you need to grant it access to Unity Catalog volumes. **The deployment script will remind you to do this.**

**Step 1:** Get the grant commands (with your app's UUID auto-detected)
```bash
./show_grant_commands.sh
```

**Step 2:** Copy the SQL output and run in **Databricks SQL Editor**

Example output (your UUID will be different):
```sql
-- Grant permissions to app service principal (example - your UUID will differ)
GRANT USE CATALOG ON CATALOG vikcbl_payer_dev TO `f929495c-0f31-476b-b554-29af04b27179`;
GRANT USE SCHEMA ON SCHEMA vikcbl_payer_dev.cobol_migration TO `f929495c-0f31-476b-b554-29af04b27179`;
GRANT READ VOLUME ON VOLUME vikcbl_payer_dev.cobol_migration.legacy_cobol TO `f929495c-0f31-476b-b554-29af04b27179`;
GRANT SELECT ON CATALOG vikcbl_payer_dev TO `f929495c-0f31-476b-b554-29af04b27179`;
GRANT USE CATALOG ON CATALOG vikcbl_payer_analyst_dev TO `f929495c-0f31-476b-b554-29af04b27179`;
GRANT SELECT ON CATALOG vikcbl_payer_analyst_dev TO `f929495c-0f31-476b-b554-29af04b27179`;
```

**Why manual?** Unity Catalog permission grants require specific admin privileges that may not be available to automation scripts. This one-time step (takes 30 seconds) ensures the app can access volumes containing COBOL files.

**Verify:** Check **Catalog Explorer** → **vikcbl_payer_dev.cobol_migration.legacy_cobol** → **Permissions** tab to confirm the app has access.

### Via Databricks CLI (Manual)

```bash
# For Streamlit app
databricks bundle deploy --var="user_prefix=vikcbl" --profile DEFAULT_azure
databricks apps deploy vikcbl-cobol-converter --profile DEFAULT_azure

# For Databricks Assistant
databricks workspace import --overwrite \
  --file config/.assistant_instructions.md \
  /Workspace/Users/your.email@company.com/.assistant_instructions.md
```

---

## Configuration

### Environment Variables (dashboard/app.yaml)

```yaml
env:
  - name: "DATABRICKS_HOST"
    value: "your-workspace.azuredatabricks.net"
  
  - name: "SERVING_ENDPOINT_NAME"
    value: "databricks-claude-sonnet-4-5"
  
  - name: "MAX_TOKENS"
    value: "8000"
```

### Customization

See `config/.assistant_instructions.md` for:
- COBOL → PySpark conversion patterns
- Healthcare payer-specific rules
- COBOL data type mappings (COMP-3, PIC V, REDEFINES)
- 15 critical COBOL conversion gotchas
- Data quality validation patterns
- Error handling strategies

---

## Testing

After deployment:

1. Test PySpark conversion (should include `overwriteSchema=true`)
2. Test SQL conversion (should show warning about duplicate columns)
3. Verify imports work (`from file_handler import ...`)
4. Check notebooks run successfully

---

## Troubleshooting

### Common Issues

1. **Import errors after restructure**: Verify `file_handler.py` and `utils.py` are in `dashboard/` root
2. **Rate limit errors**: Check Foundation Model API quotas in Databricks workspace
3. **COLUMN_ALREADY_EXISTS errors**: Read SQL notebook warning, use `SELECT * REPLACE`
4. **DELTA_FAILED_TO_MERGE_FIELDS**: Add `overwriteSchema=true` to table writes

### Logs

```bash
# Check app logs
databricks apps logs vikcbl-cobol-converter --profile DEFAULT_azure

# Check bundle status
databricks bundle validate --var="user_prefix=vikcbl"
```

---

## Personal Setup (Optional)

This project uses comprehensive instruction files for optimal LLM conversion. You can:

1. **Use as-is**: The included `.assistant_instructions.md` files work out of the box
2. **Customize**: Copy `.assistant_instructions.md` to your own environment tracking
3. **Extend**: Add your own industry-specific rules and patterns

Note: The authors use centralized configuration management for personal development, but this is optional.

---

## Contributing

This is production code from a 3-day development sprint with comprehensive lessons learned. Key improvements validated:

- 12 critical conversion rules
- Claude Sonnet 4.5 integration
- Comprehensive error prevention
- Healthcare payer-specific patterns

Contributions welcome! Please test thoroughly before submitting PRs.

---

## License

MIT License - See LICENSE file for details

---

## Support

For issues or questions:
1. Review the comprehensive `.assistant_instructions.md` for conversion patterns
2. Check troubleshooting section above for common issues
3. Test with `./deploy_streamlit_app.sh` for quick app iterations
4. Or use `./setup_databricks_assistant.sh` for notebook-based conversions
5. Open an issue on GitHub with details and error logs

---

## Version History

- **v2.4** (Current): Pure SQL mode with warnings, Claude Sonnet 4.5 integration
- **v2.3**: Hybrid mode implementation
- **v2.2**: Comprehensive validation rules
- **v2.1**: Initial production release

---

**Built with Databricks Foundation Models | Optimized for Healthcare Payers**
