# Databricks notebook source
# MAGIC %md
# MAGIC # COBOL Demo 2: Claims Analytics - Denied Claims Report
# MAGIC **Objective**: Convert COBOL batch job for denied claims analysis to PySpark
# MAGIC
# MAGIC **Demo Flow**:
# MAGIC 1. See legacy COBOL code below
# MAGIC 2. Copy and paste into empty cell
# MAGIC 3. Invoke Databricks Assistant to convert COBOL → PySpark

# COMMAND ----------

# Configuration widgets with vikcbl defaults
dbutils.widgets.text("source_catalog", "vikcbl_payer_dev")
dbutils.widgets.text("target_catalog", "vikcbl_payer_analyst_dev")

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
# MAGIC PROGRAM-ID. CLAIMS-DENIED-ANALYSIS.
# MAGIC AUTHOR. CLAIMS-TEAM.
# MAGIC
# MAGIC DATA DIVISION.
# MAGIC WORKING-STORAGE SECTION.
# MAGIC 01  WS-CLAIM-STATUS    PIC X(10) VALUE 'Denied'.
# MAGIC 01  WS-TOTAL-CLAIMS    PIC 9(7) VALUE 0.
# MAGIC 01  WS-TOTAL-BILLED    PIC 9(9)V99 VALUE 0.
# MAGIC 01  WS-PROVIDER-COUNT  PIC 9(5) VALUE 0.
# MAGIC
# MAGIC PROCEDURE DIVISION.
# MAGIC MAIN-PROCESS.
# MAGIC     PERFORM READ-CLAIMS
# MAGIC     PERFORM CALCULATE-STATS
# MAGIC     PERFORM WRITE-REPORT
# MAGIC     STOP RUN.
# MAGIC
# MAGIC READ-CLAIMS.
# MAGIC     * Read from PAYER-DEV.ANALYTICS-GOLD.CLAIMS
# MAGIC     * Filter WHERE CLAIM-STATUS = 'Denied'
# MAGIC     * Filter WHERE SERVICE-DATE >= '2023-01-01'
# MAGIC     * Join with PROVIDERS table on PROVIDER-ID
# MAGIC     
# MAGIC CALCULATE-STATS.
# MAGIC     * GROUP BY PROVIDER-ID, PROVIDER-NAME, PROCEDURE-CODE
# MAGIC     * COUNT(*) as DENIED-CLAIM-COUNT
# MAGIC     * SUM(BILLED-AMOUNT) as TOTAL-BILLED-AMOUNT
# MAGIC     * Order by DENIED-CLAIM-COUNT DESC
# MAGIC     
# MAGIC WRITE-REPORT.
# MAGIC     * Write to PAYER-ANALYST-DEV.CLAIMS-ANALYTICS.DENIED-CLAIMS-REPORT
# MAGIC ```

# COMMAND ----------

# 🎯 LIVE DEMO: Paste COBOL code here and invoke Assistant (Cmd+I)
#
# Expected conversion:
# - Join vikcbl_payer_dev.analytics_gold.claims with providers
# - Filter denied claims from 2023
# - Group by provider and procedure
# - Write to vikcbl_payer_analyst_dev.claims_analytics.denied_claims_report

# [PASTE COBOL CODE HERE AND INVOKE ASSISTANT]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference: Expected Conversion
# MAGIC
# MAGIC ```python
# MAGIC from pyspark.sql import functions as F
# MAGIC
# MAGIC # Read tables
# MAGIC claims_df = spark.table(f"{SOURCE_CATALOG}.analytics_gold.claims")
# MAGIC providers_df = spark.table(f"{SOURCE_CATALOG}.analytics_gold.providers")
# MAGIC
# MAGIC # Filter denied claims from 2023
# MAGIC denied_df = claims_df.filter(
# MAGIC     (F.col("claim_status") == "Denied") &
# MAGIC     (F.col("service_date") >= "2023-01-01")
# MAGIC )
# MAGIC
# MAGIC # Join with providers
# MAGIC joined_df = denied_df.join(providers_df, "provider_id", "inner")
# MAGIC
# MAGIC # Calculate statistics
# MAGIC report_df = joined_df.groupBy(
# MAGIC     "provider_id", "provider_name", "procedure_code"
# MAGIC ).agg(
# MAGIC     F.count("*").alias("denied_claim_count"),
# MAGIC     F.sum("billed_amount").alias("total_billed_amount")
# MAGIC ).orderBy(F.desc("denied_claim_count"))
# MAGIC
# MAGIC # Write results
# MAGIC report_df.write.mode("overwrite").saveAsTable(
# MAGIC     f"{TARGET_CATALOG}.claims_analytics.denied_claims_report"
# MAGIC )
# MAGIC
# MAGIC display(report_df)
# MAGIC ```

# COMMAND ----------

