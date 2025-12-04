# Databricks notebook source
# MAGIC %md
# MAGIC # COBOL Demo 1: HEDIS BCS Measure (Breast Cancer Screening)
# MAGIC **Objective**: Convert mainframe COBOL batch program to PySpark for HEDIS quality reporting
# MAGIC
# MAGIC **Demo Flow**:
# MAGIC 1. See legacy COBOL code below (from mainframe)
# MAGIC 2. Copy the COBOL code
# MAGIC 3. Paste into the empty cell and invoke Databricks Assistant (Cmd+I or Ctrl+I)
# MAGIC 4. Watch AI convert COBOL → PySpark using your catalogs!

# COMMAND ----------

# Configuration - Extract user prefix with "cbl" suffix for COBOL
current_user = spark.sql("SELECT current_user() as user").collect()[0]["user"]
user_prefix = current_user.split('@')[0].split('.')[0].lower() + "cbl"

# Configuration widgets with dynamic defaults
dbutils.widgets.text("source_catalog", f"{user_prefix}_payer_dev")
dbutils.widgets.text("target_catalog", f"{user_prefix}_payer_analyst_dev")

SOURCE_CATALOG = dbutils.widgets.get("source_catalog")
TARGET_CATALOG = dbutils.widgets.get("target_catalog")

print(f"✅ Source: {SOURCE_CATALOG}")
print(f"✅ Target: {TARGET_CATALOG}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Legacy COBOL Code from Mainframe
# MAGIC
# MAGIC ```cobol
# MAGIC IDENTIFICATION DIVISION.
# MAGIC PROGRAM-ID. HEDIS-BCS-SUMMARY.
# MAGIC AUTHOR. PAYER-ANALYTICS-TEAM.
# MAGIC
# MAGIC DATA DIVISION.
# MAGIC WORKING-STORAGE SECTION.
# MAGIC 01  WS-MEASURE-YEAR    PIC 9(4) VALUE 2023.
# MAGIC 01  WS-MIN-AGE         PIC 99 VALUE 50.
# MAGIC 01  WS-MAX-AGE         PIC 99 VALUE 74.
# MAGIC 01  WS-MEASURE-ID      PIC XXX VALUE 'BCS'.
# MAGIC 01  WS-AGE-GROUP       PIC X(10).
# MAGIC 01  WS-NUMERATOR       PIC 9(7) VALUE 0.
# MAGIC 01  WS-DENOMINATOR     PIC 9(7) VALUE 0.
# MAGIC 01  WS-COMPLIANCE-PCT  PIC 999V99.
# MAGIC
# MAGIC PROCEDURE DIVISION.
# MAGIC MAIN-LOGIC.
# MAGIC     PERFORM READ-HEDIS-DATA
# MAGIC     PERFORM APPLY-EXCLUSIONS
# MAGIC     PERFORM CALCULATE-SUMMARY
# MAGIC     PERFORM WRITE-RESULTS
# MAGIC     STOP RUN.
# MAGIC
# MAGIC READ-HEDIS-DATA.
# MAGIC     * Read from PAYER-DEV.ANALYTICS-GOLD.HEDIS-MEASURES
# MAGIC     * Filter WHERE MEASURE-ID = 'BCS'
# MAGIC     * Filter WHERE AGE BETWEEN 50 AND 74
# MAGIC     * Filter WHERE MEASURE-YEAR = 2023
# MAGIC     
# MAGIC APPLY-EXCLUSIONS.
# MAGIC     * Remove records where EXCLUSION = 1
# MAGIC     * (hospice, bilateral mastectomy, etc.)
# MAGIC     
# MAGIC CALCULATE-SUMMARY.
# MAGIC     * GROUP BY AGE-GROUP
# MAGIC     * SUM(DENOMINATOR) as DENOMINATOR
# MAGIC     * SUM(NUMERATOR) as NUMERATOR
# MAGIC     * COMPUTE COMPLIANCE-PCT = (NUMERATOR / DENOMINATOR) * 100
# MAGIC     
# MAGIC WRITE-RESULTS.
# MAGIC     * Write to PAYER-ANALYST-DEV.HEDIS-REPORTS.BCS-SUMMARY
# MAGIC ```

# COMMAND ----------

# 🎯 LIVE DEMO INSTRUCTIONS:
#
# 1. Copy the COBOL code from the markdown cell above
# 2. Paste it into this cell
# 3. Add comment: "Convert this COBOL to PySpark using my catalogs"
# 4. Invoke Databricks Assistant (Cmd+I or Ctrl+I)
# 5. Watch AI generate PySpark code!
#
# Expected output:
# - Reads from: {SOURCE_CATALOG}.analytics_gold.hedis_measures
# - Writes to: {TARGET_CATALOG}.hedis_reports.bcs_summary
# - Uses catalog variables from widgets

# [PASTE COBOL CODE HERE AND INVOKE ASSISTANT]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference: Expected Conversion Output
# MAGIC
# MAGIC The Assistant should generate PySpark code similar to:
# MAGIC
# MAGIC ```python
# MAGIC from pyspark.sql import functions as F
# MAGIC
# MAGIC # Read HEDIS measures
# MAGIC hedis_df = spark.table(f"{SOURCE_CATALOG}.analytics_gold.hedis_measures")
# MAGIC
# MAGIC # Filter for BCS measure, age range, and year
# MAGIC bcs_df = hedis_df.filter(
# MAGIC     (F.col("measure_id") == "BCS") &
# MAGIC     (F.col("age").between(50, 74)) &
# MAGIC     (F.col("measure_year") == 2023) &
# MAGIC     (F.col("exclusion") == 0)  # Apply exclusions
# MAGIC )
# MAGIC
# MAGIC # Calculate summary by age group
# MAGIC summary_df = bcs_df.groupBy("age_group").agg(
# MAGIC     F.sum("denominator").alias("denominator"),
# MAGIC     F.sum("numerator").alias("numerator")
# MAGIC ).withColumn(
# MAGIC     "compliance_pct",
# MAGIC     (F.col("numerator") / F.col("denominator") * 100).cast("decimal(5,2)")
# MAGIC )
# MAGIC
# MAGIC # Write results
# MAGIC summary_df.write.mode("overwrite").saveAsTable(
# MAGIC     f"{TARGET_CATALOG}.hedis_reports.bcs_summary"
# MAGIC )
# MAGIC
# MAGIC display(summary_df)
# MAGIC ```

# COMMAND ----------


