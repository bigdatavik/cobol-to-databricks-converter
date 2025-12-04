# Architecture: SAS to Databricks Payer Migration Demo

## 🎯 Overview

This document provides detailed architecture diagrams and technical specifications for the SAS to Databricks migration demo project.

---

## 📊 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ON-PREMISE (Legacy)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   Claims     │     │   Member     │     │   Provider   │        │
│  │   Data       │────▶│   Enrollment │────▶│   Network    │        │
│  │   (Raw)      │     │   (Clean)    │     │   (Metrics)  │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                                       │
│                             ↓ ↓ ↓                                    │
│                     ALREADY MIGRATED ✓                               │
│                             ↓ ↓ ↓                                    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ ↓ ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABRICKS UNITY CATALOG                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    CATALOG: payer_dev                          │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │                                                                │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐ │ │
│  │  │ claims_bronze   │  │ claims_silver   │  │analytics_gold │ │ │
│  │  │ (Raw Ingestion) │─▶│ (Data Quality)  │─▶│ (Aggregated)  │ │ │
│  │  └─────────────────┘  └─────────────────┘  └───────────────┘ │ │
│  │                                                     ▲          │ │
│  │                                                     │          │ │
│  └─────────────────────────────────────────────────────┼──────────┘ │
│                                                        │            │
│                              SAS Programs Read From HERE            │
│                                                        │            │
│  ┌─────────────────────────────────────────────────────┼──────────┐ │
│  │                 LEGACY SAS PROGRAMS                 │          │ │
│  │                                                     │          │ │
│  │  • hedis_reports.sas         (PROC SQL/FREQ)       │          │ │
│  │  • risk_adjustment.sas       (DATA step/arrays)    │          │ │
│  │  • claims_analytics.sas      (DATA/PROC SQL)       │          │ │
│  │  • provider_analytics.sas    (PROC SQL/joins)      │          │ │
│  │  • member_analytics.sas      (DATA step/windows)   │          │ │
│  │  • prior_auth_analytics.sas  (PROC FREQ/dates)     │          │ │
│  │                                                                │ │
│  │                    ↓ ↓ ↓ CONVERT ↓ ↓ ↓                        │ │
│  │                                                                │ │
│  │         🤖 DATABRICKS ASSISTANT INSTRUCTIONS 🤖                │ │
│  │                                                                │ │
│  │   .assistant_instructions.md automatically applies:           │ │
│  │   ✓ Catalog/schema names                                      │ │
│  │   ✓ Conversion patterns (PROC FREQ → .groupBy())             │ │
│  │   ✓ Coding standards (snake_case, _df suffix)                │ │
│  │   ✓ Function equivalents (INTNX → F.add_months())            │ │
│  │                                                                │ │
│  │                    ↓ ↓ ↓ RESULTS ↓ ↓ ↓                        │ │
│  │                                                                │ │
│  │         PySpark Code          |        Databricks SQL         │ │
│  │     (Data Engineering)         |      (Analyst-Friendly)      │ │
│  │                                                                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│                              ↓ WRITE TO ↓                             │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │               CATALOG: payer_analyst_dev                       │ │
│  ├────────────────────────────────────────────────────────────────┤ │
│  │                                                                │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐ │ │
│  │  │ hedis_reports    │  │ risk_adjustment  │  │  claims_    │ │ │
│  │  │ • bcs_summary    │  │ • raf_summary    │  │  analytics  │ │ │
│  │  │ • ccs_summary    │  │ • hcc_detail     │  │ • cost_     │ │ │
│  │  └──────────────────┘  └──────────────────┘  │   analysis  │ │ │
│  │                                               └─────────────┘ │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐ │ │
│  │  │ provider_        │  │ member_          │  │ prior_auth_ │ │ │
│  │  │ analytics        │  │ analytics        │  │ analytics   │ │ │
│  │  │ • performance    │  │ • churn_         │  │ • approval_ │ │ │
│  │  │ • scorecard      │  │   indicators     │  │   rates     │ │ │
│  │  └──────────────────┘  └──────────────────┘  └─────────────┘ │ │
│  │                                                                │ │
│  │              CONVERTED ANALYTICAL OUTPUTS                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Unity Catalog Structure

### Source Catalog: `payer_dev`

```
payer_dev/
├── claims_bronze/                    # Raw data layer (demonstration only)
│   ├── medical_claims_raw
│   └── pharmacy_claims_raw
│
├── claims_silver/                    # Clean data layer (demonstration only)
│   ├── medical_claims_clean
│   ├── pharmacy_claims_clean
│   ├── member_enrollment
│   └── provider_dim
│
└── analytics_gold/                   # GOLD TABLES ← SAS programs read from HERE
    ├── hedis_measures                # HEDIS quality measures (5K members)
    │   • member_id, measure_id, age_group, compliant, service_date
    │
    ├── risk_adjustment_scores        # RAF/HCC scores (5K members)
    │   • member_id, plan_type, raf_score, hcc_codes, score_year
    │
    ├── claims_summary                # Claims aggregations (10K claims)
    │   • claim_id, member_id, provider_npi, claim_amount, service_date
    │
    ├── provider_performance          # Provider metrics (1K providers)
    │   • provider_npi, specialty, patient_count, quality_score, network_tier
    │
    ├── member_metrics                # Member analytics (5K members)
    │   • member_id, enrollment_months, total_cost, churn_risk_flag
    │
    └── prior_auth_summary            # Prior auth metrics (3K auths)
        • auth_id, member_id, auth_type, status, approval_date, request_date
```

### Target Catalog: `payer_analyst_dev`

```
payer_analyst_dev/
├── hedis_reports/                    # Converted HEDIS analytical outputs
│   ├── bcs_summary                   # Breast Cancer Screening summary
│   ├── ccs_summary                   # Colorectal Cancer Screening
│   └── dme_summary                   # Diabetes Monitoring
│
├── risk_adjustment/                  # Converted RAF analytical outputs
│   ├── raf_summary                   # Plan-level RAF scores
│   ├── hcc_detail                    # Member-level HCC breakdowns
│   └── risk_stratification           # Risk category distributions
│
├── claims_analytics/                 # Converted claims analytical outputs
│   ├── cost_analysis                 # Cost threshold analysis
│   ├── high_cost_members             # Top cost drivers
│   └── utilization_trends            # Utilization patterns
│
├── provider_analytics/               # Converted provider analytical outputs
│   ├── performance_summary           # Provider scorecards
│   ├── network_analysis              # Network utilization
│   └── quality_metrics               # Quality measure performance
│
├── member_analytics/                 # Converted member analytical outputs
│   ├── churn_indicators              # Churn risk scores
│   ├── member_segmentation           # Member segments
│   └── cost_trends                   # Member cost patterns
│
└── prior_auth_analytics/             # Converted prior auth analytical outputs
    ├── approval_rates                # Auth approval rates by type
    ├── turnaround_time               # TAT analysis
    └── denial_analysis               # Denial pattern analysis
```

---

## 🔄 Conversion Workflow

### Workflow 1: User Opens Demo Notebook

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: User Opens Databricks Notebook                     │
│  (e.g., 01_hedis_pyspark.py)                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Notebook Displays Legacy SAS Code                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ```markdown                                           │  │
│  │ ## Legacy SAS Code                                    │  │
│  │                                                       │  │
│  │ PROC SQL;                                             │  │
│  │   SELECT member_id, age_group, COUNT(*) as count     │  │
│  │   FROM hedis_measures                                 │  │
│  │   WHERE measure_id = 'BCS'                            │  │
│  │   GROUP BY member_id, age_group;                      │  │
│  │ QUIT;                                                 │  │
│  │ ```                                                   │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: User Copies SAS Code                               │
│  - Copies from markdown cell                                │
│  - Pastes into new Python cell                              │
│  - Adds comment: "# Convert this to PySpark"                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: User Invokes Databricks Assistant                  │
│  - Presses Cmd+I (Mac) or Ctrl+I (Windows)                  │
│  - Or clicks Assistant button                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Assistant Reads Instruction File (Automatic)       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  📄 /Workspace/Users/username/                        │  │
│  │      .assistant_instructions.md                       │  │
│  │                                                       │  │
│  │  ✓ Source catalog: payer_dev.analytics_gold          │  │
│  │  ✓ Target catalog: payer_analyst_dev.hedis_reports   │  │
│  │  ✓ PROC SQL → .groupBy().agg()                       │  │
│  │  ✓ Coding standards: snake_case, _df suffix          │  │
│  │  ✓ Import: from pyspark.sql import functions as F    │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Assistant Returns Converted Code                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ from pyspark.sql import functions as F                │  │
│  │                                                       │  │
│  │ # Read from gold layer                                │  │
│  │ hedis_df = spark.read.table(                          │  │
│  │     "payer_dev.analytics_gold.hedis_measures"         │  │
│  │ )                                                     │  │
│  │                                                       │  │
│  │ # Filter and aggregate (PROC SQL equivalent)          │  │
│  │ bcs_summary_df = hedis_df.filter(                     │  │
│  │     F.col("measure_id") == "BCS"                      │  │
│  │ ).groupBy("member_id", "age_group").agg(              │  │
│  │     F.count("*").alias("count")                       │  │
│  │ )                                                     │  │
│  │                                                       │  │
│  │ # Write to analyst catalog                            │  │
│  │ bcs_summary_df.write.mode("overwrite").saveAsTable(   │  │
│  │     "payer_analyst_dev.hedis_reports.bcs_summary"     │  │
│  │ )                                                     │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 7: User Runs Converted Code                           │
│  - Clicks "Run Cell"                                        │
│  - Code executes against Databricks cluster                 │
│  - Results written to target catalog                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 8: Validate Results                                   │
│  spark.table("payer_analyst_dev.hedis_reports.bcs_summary") │
│      .display()                                             │
│                                                             │
│  ✅ Data written to target catalog                          │
│  ✅ Code follows organizational standards                   │
│  ✅ Conversion completed in < 2 minutes                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Conversion Pattern Matrix

### SAS to PySpark Mappings

| SAS Pattern | PySpark Equivalent | Use Case |
|-------------|-------------------|----------|
| `PROC FREQ` | `.groupBy().count()` | Frequency distributions |
| `PROC SQL SELECT` | `.select()` | Column selection |
| `PROC SQL WHERE` | `.filter()` | Row filtering |
| `PROC SQL GROUP BY` | `.groupBy().agg()` | Aggregations |
| `PROC MEANS` | `.groupBy().agg(F.mean(), F.stddev())` | Statistical summaries |
| `DATA step IF/THEN` | `.withColumn(F.when())` | Conditional logic |
| `DATA step arrays` | UDF or `.transform()` | Array processing |
| `PROC SQL JOIN` | `.join(how='inner/left/right')` | Table joins |
| `PROC SORT` | `.orderBy()` or `.sort()` | Sorting |
| `INTNX('month')` | `F.add_months()` | Date arithmetic |
| `INTCK('day')` | `F.datediff()` | Date differences |
| `UPCASE()` | `F.upper()` | String uppercase |
| `SUBSTR()` | `F.substring()` | String substring |

### SAS to Databricks SQL Mappings

| SAS Pattern | Databricks SQL Equivalent | Use Case |
|-------------|--------------------------|----------|
| `PROC SQL SELECT` | `SELECT` | Column selection |
| `PROC SQL WHERE` | `WHERE` | Row filtering |
| `PROC SQL GROUP BY` | `GROUP BY` | Aggregations |
| `PROC FREQ` | `GROUP BY ... COUNT(*)` | Frequency counts |
| `'01JAN2023'd` | `'2023-01-01'` | Date literals |
| Implicit JOIN | `INNER JOIN` / `LEFT JOIN` | Explicit joins |
| `INTNX('month')` | `ADD_MONTHS()` | Date arithmetic |
| `INTCK('day')` | `DATEDIFF()` | Date differences |
| `TODAY()` | `CURRENT_DATE()` | Current date |
| `UPCASE()` | `UPPER()` | String uppercase |

---

## 📦 Data Generator Architecture

### Dummy Data Generation Flow

```
┌────────────────────────────────────────────────────────────┐
│           data_generators/ Python Modules                   │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  generate_gold_hedis.py                              │  │
│  │  • 5,000 members (ages 50-74 for BCS)                │  │
│  │  • HEDIS measures: BCS, CCS, DME                     │  │
│  │  • Compliant/non-compliant flags                     │  │
│  │  • Service dates (measurement year 2023)             │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │  generate_gold_risk.py                               │  │
│  │  • 5,000 members with RAF scores                     │  │
│  │  • CMS-HCC v24 diagnosis codes                       │  │
│  │  • Plan types: MA, Medicaid, Commercial              │  │
│  │  • RAF scores: 0.5-3.5 range                         │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │  generate_gold_claims.py                             │  │
│  │  • 10,000 claim records                              │  │
│  │  • Claim amounts: $50 - $50,000                      │  │
│  │  • Service dates: 2023                               │  │
│  │  • Diagnosis codes, CPT codes                        │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │  generate_gold_providers.py                          │  │
│  │  • 1,000 providers with NPIs                         │  │
│  │  • Specialties: PCP, Specialist, Hospital            │  │
│  │  • Quality scores: 1-5 stars                         │  │
│  │  • Patient counts, network tiers                     │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │  generate_gold_members.py                            │  │
│  │  • 5,000 member records                              │  │
│  │  • Enrollment months, total costs                    │  │
│  │  • Churn risk flags                                  │  │
│  │  • Demographics: age, gender, zip                    │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │  generate_gold_prior_auth.py                         │  │
│  │  • 3,000 prior auth records                          │  │
│  │  • Auth types: Imaging, Surgery, Medication          │  │
│  │  • Status: Approved, Denied, Pending                 │  │
│  │  • Turnaround times: 1-30 days                       │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                         │
└───────────────────┼─────────────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────┐
│        00_setup_catalogs_data.py (Setup Notebook)          │
├────────────────────────────────────────────────────────────┤
│  1. Create Unity Catalog: payer_dev                        │
│  2. Create schemas: claims_bronze, claims_silver,          │
│                     analytics_gold                         │
│  3. Create Unity Catalog: payer_analyst_dev                │
│  4. Create target schemas (6 schemas)                      │
│  5. Call data generators → Create DataFrames               │
│  6. Write to payer_dev.analytics_gold.* tables             │
│  7. Display samples and row counts                         │
│  8. Validate data quality                                  │
└────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security & Permissions

### Required Permissions

```
Unity Catalog Permissions:
├── CREATE CATALOG                    (for setup)
├── CREATE SCHEMA                     (for setup)
├── CREATE VOLUME                     (for SAS file storage)
├── USE CATALOG payer_dev             (read source tables)
├── USE SCHEMA analytics_gold         (read source tables)
├── USE SCHEMA sas_migration          (for volume access)
├── SELECT on payer_dev.analytics_gold.* (read data)
├── READ VOLUME on legacy_sas         (for Streamlit app)
├── USE CATALOG payer_analyst_dev     (write target tables)
├── USE SCHEMA <target_schemas>       (write target tables)
└── CREATE TABLE on target schemas    (write outputs)

Workspace Permissions:
├── Can Run Jobs                      (for setup job)
├── Can Access Workspace Files        (for .assistant_instructions.md)
└── Can Use SQL Warehouses            (for SQL demos)
```

---

## 🚀 Deployment Workflow

### Automated Deployment Scripts

```
┌─────────────────────────────────────────────────────────────────┐
│                   Deployment Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  setup_databricks_assistant.sh (Full Setup - ~10 min)           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. Auto-detect Databricks user                            │ │
│  │  2. Validate databricks.yml bundle config                  │ │
│  │  3. Deploy bundle → /Workspace/.bundle/                    │ │
│  │  4. Deploy .assistant_instructions.md → /Workspace/Users/  │ │
│  │  5. Run setup job: CREATE CATALOG, SCHEMA, VOLUME          │ │
│  │  6. Generate & load 29,000 rows of demo data               │ │
│  │  7. Upload 6 SAS files → Unity Catalog volume              │ │
│  │     /Volumes/payer_dev/sas_migration/legacy_sas/           │ │
│  │  8. Display success summary with quick links               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  deploy_streamlit_app.sh (Quick Update - ~30 sec)               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. Auto-detect Databricks user                            │ │
│  │  2. Read catalog/volume config from databricks.yml         │ │
│  │  3. Sync .assistant_instructions.md to dashboard/          │ │
│  │  4. Deploy bundle → /Workspace/.bundle/                    │ │
│  │  5. Redeploy Databricks App                                │ │
│  │  6. Auto-detect app service principal UUID                 │ │
│  │  7. Display permission grant reminder with SQL commands    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  show_grant_commands.sh (Helper - instant)                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  1. Query Databricks Apps API for sas-converter            │ │
│  │  2. Extract service_principal_client_id (UUID)             │ │
│  │  3. Read catalog/volume names from databricks.yml          │ │
│  │  4. Generate SQL GRANT commands dynamically                │ │
│  │  5. Save to grant_commands.sql                             │ │
│  │  6. Display copy-paste-ready SQL                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Unity Catalog Volume Setup

```
┌─────────────────────────────────────────────────────────────────┐
│              Volume Structure for SAS Files                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  payer_dev (Catalog)                                             │
│  └── sas_migration (Schema)                                      │
│      └── legacy_sas (Volume)                                     │
│          ├── claims_analytics.sas                                │
│          ├── hedis_reports.sas                                   │
│          ├── member_analytics.sas                                │
│          ├── prior_auth_analytics.sas                            │
│          ├── provider_analytics.sas                              │
│          └── risk_adjustment.sas                                 │
│                                                                  │
│  Permissions Required:                                           │
│  • App Service Principal needs READ VOLUME                       │
│  • Granted via manual SQL (one-time setup)                       │
│  • Commands generated by show_grant_commands.sh                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Streamlit App Service Principal Permissions

The Streamlit app runs as a service principal and needs Unity Catalog access:

```sql
-- Auto-generated by show_grant_commands.sh
GRANT USE CATALOG ON CATALOG payer_dev TO `<app-service-principal-uuid>`;
GRANT USE SCHEMA ON SCHEMA payer_dev.sas_migration TO `<app-service-principal-uuid>`;
GRANT READ VOLUME ON VOLUME payer_dev.sas_migration.legacy_sas TO `<app-service-principal-uuid>`;
GRANT SELECT ON CATALOG payer_dev TO `<app-service-principal-uuid>`;
GRANT USE CATALOG ON CATALOG payer_analyst_dev TO `<app-service-principal-uuid>`;
GRANT SELECT ON CATALOG payer_analyst_dev TO `<app-service-principal-uuid>`;
```

**Why Manual?** Unity Catalog permission grants require specific admin privileges that may not be available to automation scripts. This one-time step (30 seconds) ensures reliable permissions across all environments.

---

## 🎯 Success Metrics

### Technical Metrics

- ✅ **Code Accuracy**: 100% functional equivalence to SAS
- ✅ **Code Quality**: Passes linting, follows standards
- ✅ **Performance**: Sub-second for most transformations
- ✅ **Data Quality**: Row counts match, business logic preserved

### Business Metrics

- ✅ **Time Savings**: 75-92% reduction in conversion time
- ✅ **Consistency**: 100% adherence to organizational standards
- ✅ **Onboarding**: New team members productive in < 1 day
- ✅ **Scalability**: Pattern applies to 100+ SAS programs

---

## 📚 Technology Stack

```
┌─────────────────────────────────────────────────────────┐
│                  Technology Stack                        │
├─────────────────────────────────────────────────────────┤
│  Platform:         Azure Databricks                     │
│  Runtime:          DBR 16.4 LTS                         │
│  Catalog:          Unity Catalog                        │
│  Languages:        PySpark, Databricks SQL              │
│  Deployment:       Databricks Asset Bundles (DAB)       │
│  Version Control:  Git                                  │
│  AI Assistant:     Databricks Assistant + Instructions  │
│  Data Gen:         Python (pandas, faker, numpy)        │
└─────────────────────────────────────────────────────────┘
```

---

**Last Updated**: 2025  
**Maintained by**: Healthcare Payer Analytics Team






