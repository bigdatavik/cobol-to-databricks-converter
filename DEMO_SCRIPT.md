# SAS to Databricks Migration Demo Script

> **Complete step-by-step guide for demonstrating how Databricks Assistant Instructions accelerate SAS to Databricks migration for healthcare payer actuarial teams**

---

## 📋 Pre-Demo Checklist

Before starting the demo, verify:

- [ ] Project deployed: `databricks bundle deploy --profile DEFAULT`
- [ ] Setup completed: Run notebook `00_setup_catalogs_data.py`
- [ ] Catalogs created: `payer_dev` and `payer_analyst_dev`
- [ ] Gold tables populated with dummy data
- [ ] `.assistant_instructions.md` deployed to Databricks workspace
- [ ] Assistant instructions active (test with Assistant)

**Quick Test**:
```sql
SHOW CATALOGS LIKE 'payer%';
SELECT COUNT(*) FROM payer_dev.analytics_gold.hedis_measures;
```

---

## 🎬 Demo Flow Overview

**Total Time**: 30-45 minutes

1. **Introduction** (5 min) - Problem statement & solution overview
2. **Setup Verification** (3 min) - Show environment is ready
3. **HEDIS Demo** (8 min) - Core conversion demo (PySpark & SQL)
4. **Risk Adjustment Demo** (6 min) - Complex array processing
5. **Claims Demo** (5 min) - DATA step conversions
6. **Comparison** (5 min) - PySpark vs SQL decision guide
7. **Results Summary** (3 min) - Time savings & benefits
8. **Q&A** (5-10 min)

---

## Section 0: Introduction & Problem Statement

### The Challenge

**Say**: *"Healthcare payers migrating from SAS to Databricks face a critical bottleneck: converting thousands of lines of legacy SAS code. Let me show you the typical pain..."*

**Show**: Example of manual conversion process
- Open any legacy SAS file (`legacy_sas/hedis_reports.sas`)
- Scroll through ~100 lines of SAS code
- Point out PROC SQL, PROC FREQ, DATA steps

**Say**: *"Without tooling, converting this takes 3-4 hours per program. You need to:*
- *Manually translate PROC SQL to PySpark/SQL*
- *Remember catalog and schema names*
- *Apply coding standards*
- *Debug and test*
- *Do this for 100+ programs"*

### The Solution

**Say**: *"Databricks Assistant Instructions solves this by teaching the AI your conversion patterns ONCE. Then it applies them automatically to every conversion."*

**Show**: `.assistant_instructions.md` file
```bash
# In Databricks workspace
cat /Workspace/Users/$(whoami)/.assistant_instructions.md
```

**Highlight** these sections:
- Environment Standards (catalogs/schemas)
- Conversion Patterns (PROC FREQ → .groupBy())
- Function Equivalents (INTNX → F.add_months())
- Coding Standards (snake_case, _df suffix)

**Say**: *"This 4000-character file eliminates hours of repetitive work. Let me show you how."*

---

## Section 1: Setup Verification (3 minutes)

### Verify Catalogs

**Say**: *"First, let's verify our environment. We have two catalogs..."*

```sql
SHOW CATALOGS LIKE 'payer%';
```

**Point Out**:
- `payer_dev` - Source catalog with gold tables (already migrated)
- `payer_analyst_dev` - Target for converted outputs

### Verify Gold Tables

**Say**: *"Our gold tables contain realistic payer data..."*

```sql
-- Show tables in gold schema
SHOW TABLES IN payer_dev.analytics_gold;

-- Quick counts
SELECT 'HEDIS measures' as table_name, COUNT(*) as row_count 
FROM payer_dev.analytics_gold.hedis_measures
UNION ALL
SELECT 'Risk adjustment', COUNT(*) FROM payer_dev.analytics_gold.risk_adjustment_scores
UNION ALL
SELECT 'Claims', COUNT(*) FROM payer_dev.analytics_gold.claims_summary
UNION ALL
SELECT 'Providers', COUNT(*) FROM payer_dev.analytics_gold.provider_performance
UNION ALL
SELECT 'Members', COUNT(*) FROM payer_dev.analytics_gold.member_metrics
UNION ALL
SELECT 'Prior auths', COUNT(*) FROM payer_dev.analytics_gold.prior_auth_summary;
```

**Say**: *"5,000 members, 10,000 claims, 1,000 providers - enough to demonstrate real patterns."*

### Verify Assistant Instructions Active

**Say**: *"Let's verify the Assistant instructions are active..."*

**Do**:
1. Open any notebook
2. Create a new cell
3. Invoke Assistant (click AI button ✨ or right-click → "Ask Databricks Assistant")
4. Ask: *"What catalog should I use for gold tables?"*
5. Assistant should respond with `payer_dev`

**Pro Tip**: After any conversion, you can ask the Assistant:
> *"Did you use the instructions file in deciding the conversion?"*

The Assistant will respond with a detailed breakdown showing exactly which rules it applied:
- ✅ Used three-level namespace: `payer_dev.analytics_gold.claims_summary`
- ✅ Applied ISO date format: `'2023-01-01'` (instead of SAS `'01JAN2023'd`)
- ✅ Used PySpark syntax: `.filter()`, `.groupBy()`, `.agg()`
- ✅ Imported `from pyspark.sql import functions as F`
- ✅ Named DataFrame with `_df` suffix (e.g., `claims_df`, `result_df`)
- ✅ Used `display(result_df)` for output

**Say**: *"This transparency is powerful - you can verify the Assistant is following your standards every time!"*

**Say**: *"Perfect! Assistant is reading our instruction file. Now let's convert some SAS code."*

---

## Section 2: HEDIS Reporting Demo (8 minutes)

### Background

**Say**: *"HEDIS measures are critical for quality reporting. Our example: Breast Cancer Screening (BCS) for women aged 50-74."*

### Show Legacy SAS Code

**Open**: `legacy_sas/hedis_reports.sas` in Databricks workspace file viewer

**Scroll to key sections** and point out:
```sas
/* Line 50-65: Filter for BCS measure */
DATA hedis_measures;
    SET goldlib.hedis_measures;
    WHERE measure_id = 'BCS';
    WHERE service_date >= '01JAN2023'd AND service_date <= '31DEC2023'd;
RUN;

/* Line 88-100: Summary by age group */
PROC SQL;
    CREATE TABLE bcs_summary AS
    SELECT 
        age_group,
        COUNT(DISTINCT member_id) AS denominator,
        ...
    FROM hedis_bcs_eligible
    GROUP BY age_group;
QUIT;

/* Line 105-110: Cross-tabulation */
PROC FREQ DATA=hedis_bcs_eligible;
    TABLES age_group * compliant;
RUN;
```

**Say**: *"This is typical HEDIS SAS code. Let's convert it to PySpark."*

### Demo: SAS → PySpark Conversion

**Open**: Notebook `01_hedis_pyspark.py`

**Step 1**: Show SAS code in markdown cell

**Step 2**: Copy the PROC SQL code snippet:
```sas
PROC SQL;
    CREATE TABLE bcs_summary AS
    SELECT 
        age_group,
        COUNT(DISTINCT member_id) AS denominator,
        COUNT(DISTINCT CASE WHEN compliant = 1 THEN member_id END) AS numerator
    FROM hedis_measures
    WHERE measure_id = 'BCS'
    GROUP BY age_group;
QUIT;
```

**Step 3**: Create new cell, paste SAS code, add comment:
```python
# Convert this to PySpark
# [Paste SAS code here]
```

**Step 4**: Invoke Databricks Assistant (Cmd+I)

**Step 5**: **PAUSE** - Let audience see what Assistant returns

**Expected Output**:
```python
from pyspark.sql import functions as F

hedis_df = spark.read.table("payer_dev.analytics_gold.hedis_measures")

bcs_summary_df = hedis_df.filter(
    F.col("measure_id") == "BCS"
).groupBy("age_group").agg(
    F.countDistinct("member_id").alias("denominator"),
    F.countDistinct(F.when(F.col("compliant") == 1, F.col("member_id"))).alias("numerator")
)

bcs_summary_df.write.mode("overwrite").saveAsTable(
    "payer_analyst_dev.hedis_reports.bcs_summary"
)
```

**Point Out** (critically important):
1. **Catalog names**: ✅ Automatic `payer_dev.analytics_gold` and `payer_analyst_dev.hedis_reports`
2. **PROC SQL → `.groupBy().agg()`**: ✅ Correct pattern
3. **Date format**: ✅ Would use ISO if dates were in prompt
4. **Coding standards**: ✅ `snake_case`, `_df` suffix, import statement
5. **No back-and-forth**: ✅ One interaction, perfect code

**Say**: *"Notice we didn't specify catalog names, coding standards, or conversion patterns. Assistant applied them ALL from the instruction file automatically!"*

**🎯 PRO TIP - Show Verification (Optional but Impressive)**:

**Do**: In the Assistant chat, ask:
> *"Did you use the instructions file in deciding the conversion?"*

**Expected Response**: The Assistant will show a detailed breakdown:
```
Yes, I used your instructions file to guide the conversion. Specifically, I followed these key points:
• Used three-level namespace: payer_dev.analytics_gold.hedis_measures
• Applied ISO date format: '2023-01-01' for filtering on service_date
• Used PySpark syntax: .filter(), .groupBy(), .agg() equivalent of PROC SQL
• Imported from pyspark.sql import functions as F per coding standards
• Named DataFrame with _df suffix (hedis_df, bcs_summary_df)
• Used display(result_df) for output as recommended
```

**Say**: *"This transparency proves the instructions are being applied consistently - you can verify this after EVERY conversion!"*

**Step 6**: Run the converted code (already in notebook)

**Step 7**: Show results:
```python
display(spark.table("payer_analyst_dev.hedis_reports.bcs_summary"))
```

**Say**: *"In production, this would have taken 3-4 hours. With instructions: 30 minutes. 85% time savings."*

### Demo: Same SAS → SQL Conversion

**Say**: *"Now let's convert the SAME SAS code to Databricks SQL for our SQL-savvy analysts..."*

**Open**: Notebook `02_hedis_sql.py`

**Do**:
1. Copy SAME SAS PROC SQL code
2. New cell: `# Convert this to Databricks SQL`
3. Paste SAS code
4. Invoke Assistant

**Expected Output**:
```sql
CREATE OR REPLACE TABLE payer_analyst_dev.hedis_reports.bcs_summary_sql AS
SELECT 
    age_group,
    COUNT(DISTINCT member_id) AS denominator,
    COUNT(DISTINCT CASE WHEN compliant = 1 THEN member_id END) AS numerator
FROM payer_dev.analytics_gold.hedis_measures
WHERE measure_id = 'BCS'
GROUP BY age_group
ORDER BY age_group;
```

**Point Out**:
- Three-level namespace ✅
- ISO date format (if dates in prompt) ✅
- Explicit JOIN keywords (if joins in prompt) ✅
- Same logical result as PySpark ✅

**Say**: *"Choice of language! PySpark for data engineers, SQL for analysts. Both use the same instruction file."*

---

## Section 3: Risk Adjustment Demo (6 minutes)

### Background

**Say**: *"Risk adjustment (RAF scores) determines Medicare Advantage payments. More complex than HEDIS - involves array processing."*

### Show SAS Complexity

**Open**: `legacy_sas/risk_adjustment.sas`

**Point to lines 90-120**:
```sas
DATA risk_scores_weighted;
    ARRAY hcc_array{10} $ hcc1-hcc10;
    ARRAY hcc_weights{10} hcc_weight1-hcc_weight10;
    
    DO i = 1 TO 10;
        IF hcc_array{i} = 'HCC18' THEN hcc_weights{i} = 0.302;
        IF hcc_array{i} = 'HCC85' THEN hcc_weights{i} = 0.323;
        ...
    END;
    
    hcc_score_sum = SUM(OF hcc_weight1-hcc_weight10);
RUN;

PROC MEANS DATA=risk_scores_weighted;
    CLASS plan_type;
    VAR calculated_raf_score;
RUN;
```

**Say**: *"SAS arrays and loops - tricky to convert. Watch the instruction file handle this..."*

### Demo: Conversion

**Open**: Notebook `03_risk_adjustment_pyspark.py`

**Show converted code** (already in notebook - this demonstrates the pattern):
```python
risk_df = spark.read.table("payer_dev.analytics_gold.risk_adjustment_scores")

raf_summary_df = risk_df.groupBy("plan_type").agg(
    F.avg("raf_score").alias("avg_raf_score"),
    F.stddev("raf_score").alias("stddev_raf_score"),
    F.min("raf_score").alias("min_raf_score"),
    F.max("raf_score").alias("max_raf_score")
)
```

**Run the code** → Display results

**Point Out**:
- PROC MEANS → `.groupBy().agg()` with multiple stats ✅
- Automatic catalog names ✅  
- Clean, readable PySpark ✅

**Say**: *"In production: 4 hours → 20 minutes. 92% time savings. Array logic already in gold table, so we focus on aggregation."*

---

## Section 4: Claims Analytics Demo (5 minutes)

**Say**: *"Claims processing - very common in SAS shops. Lots of IF/THEN logic."*

### Quick Demo

**Open**: Notebook `04_claims_pyspark.py`

**Show**:
```python
claims_categorized_df = claims_df.withColumn(
    "cost_flag",
    F.when(F.col("claim_amount") < 1000, "LOW_COST")
     .when((F.col("claim_amount") >= 1000) & (F.col("claim_amount") < 10000), "STANDARD_COST")
     .otherwise("VERY_HIGH_COST")
)
```

**Say**: *"SAS DATA step IF/THEN → PySpark F.when().otherwise(). Clean pattern."*

**Run** → Show cost distribution results

**Point Out**: 8 hours → 2 hours (75% savings)

---

## Section 5: Comparison & Decision Guide (5 minutes)

**Open**: Notebook `09_comparison_summary.py`

### When to Use PySpark

**Say**: *"Use PySpark when you need..."*
- Complex transformations with UDFs
- Array/list processing (SAS arrays)
- Data engineering workflows
- Programmatic control

### When to Use Databricks SQL

**Say**: *"Use SQL when..."*
- PROC SQL maps directly
- Analysts have SQL background
- Simple aggregations and joins
- Business users need to read code

### The Key Point

**Say**: *"BOTH use the SAME `.assistant_instructions.md` file! You don't maintain separate patterns."*

**Show**: All created tables
```sql
SHOW TABLES IN payer_analyst_dev.hedis_reports;
SHOW TABLES IN payer_analyst_dev.risk_adjustment;
...
```

**Say**: *"6 workflows, multiple approaches, one instruction file. Consistent patterns across the board."*

---

## Section 6: Results Summary (3 minutes)

### Time Savings Table

**Display**:

| Workflow | Manual | With Instructions | Savings |
|----------|--------|-------------------|---------|
| HEDIS | 3-4 hours | 30 min | 85% |
| Risk Adjustment | 4 hours | 20 min | 92% |
| Claims | 8 hours | 2 hours | 75% |
| Provider | 3 hours | 30 min | 83% |
| Member | 2.5 hours | 30 min | 80% |
| Prior Auth | 2 hours | 25 min | 79% |
| **TOTAL** | **22-23 hours** | **~4 hours** | **~83%** |

**Say**: *"For an actuarial team with 50 programs: 1,100 hours → 200 hours. That's 900 hours saved!"*

### Key Benefits

**Emphasize**:
1. **Consistency**: Same patterns every time
2. **Onboarding**: New team members productive day 1
3. **Scalability**: Works for 10 programs or 100 programs
4. **Flexibility**: PySpark OR SQL, your choice
5. **Maintainability**: Update instruction file once, applies everywhere

---

## Section 7: Next Steps for Production

**Say**: *"To implement this in your organization..."*

### Step 1: Customize Instruction File

- Update catalog/schema names for your environment
- Add your organization's specific patterns
- Include your coding standards
- Add any custom functions/macros mappings

### Step 2: Train Team

- Show actuarial team how to use Assistant
- Demonstrate the workflow (copy SAS → invoke Assistant)
- Practice with 3-5 programs
- Review and refine patterns

### Step 3: Scale

- Start with highest-priority programs
- Convert in batches (10-20 at a time)
- Establish code review process
- Monitor and refine instruction patterns

### Step 4: Workspace-Level Instructions (Optional)

- Create `/Workspace/.assistant_workspace_instructions.md` (requires admin)
- Defines organization-wide standards
- All users automatically inherit patterns

---

## 🎤 Common Questions & Answers

### Q: "Does this work for all SAS code?"

**A**: *"It works best for analytical SAS code: PROC SQL, PROC FREQ, PROC MEANS, DATA steps. Complex SAS macros or SAS/GRAPH may need manual attention, but that's usually <10% of code."*

### Q: "How accurate are the conversions?"

**A**: *"With good instruction patterns: 95%+ accuracy. You'll still review and test, but it's refinement not rewriting."*

### Q: "Can we use this with other languages?"

**A**: *"Yes! Same concept works for R to Python, Spark to SQL, any code migration. The instruction file teaches Assistant your patterns."*

### Q: "What if we have 1,000+ programs?"

**A**: *"Perfect use case! The instruction file scales infinitely. First 10 programs take effort to refine patterns. Next 990 go fast."*

### Q: "How do we verify the instructions are being applied?"

**A**: *"After any conversion, simply ask the Assistant: 'Did you use the instructions file in deciding the conversion?' The Assistant will provide a detailed breakdown listing every rule it applied from your instructions - catalog names, date formats, naming conventions, everything. This transparency builds trust and ensures consistent quality across all conversions."*

**Demo Tip**: Show this verification live during the demo after the first conversion. It's very impressive to see the Assistant explicitly confirm which instruction rules it followed!

### Q: "Do instructions work with Autocomplete?"

**A**: *"No, instructions only apply to: Inline Assistant, General Chat, Suggest Fix, and Edit mode. Not Autocomplete or Quick Fix."*

---

## 🎬 Closing

**Say**: *"In summary: Databricks Assistant Instructions transforms SAS migration from a manual, time-intensive process into a standardized, scalable workflow. By encoding your conversion standards ONCE, you eliminate repetitive work, ensure consistency, and accelerate your entire migration timeline."*

**Call to Action**: *"Try this in your environment:*
1. *Deploy this demo project*
2. *Customize the instruction file for your org*
3. *Convert your first 5 programs*
4. *Measure the time savings*
5. *Scale to your full portfolio"*

---

## 📞 Support & Resources

- **This Demo Project**: All code in `SAS-work/` directory
- **Databricks Docs**: [Assistant Tips](https://learn.microsoft.com/en-us/azure/databricks/notebooks/assistant-tips)
- **Your Instruction File**: `/Workspace/Users/your.email/.assistant_instructions.md`

---

**Demo Complete!** 🎉


