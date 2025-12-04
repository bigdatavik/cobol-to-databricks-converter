# Databricks notebook source
# MAGIC %md
# MAGIC # COBOL Demo 4: Risk Adjustment - HCC Scoring (PySpark)
# MAGIC **Objective**: Convert COBOL HCC risk scoring batch job to PySpark
# MAGIC
# MAGIC **Demo Flow**:
# MAGIC 1. See legacy COBOL hierarchical scoring logic
# MAGIC 2. Copy and paste into empty cell
# MAGIC 3. Invoke Assistant to convert complex COBOL → PySpark with window functions

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
# MAGIC PROGRAM-ID. HCC-RISK-SCORING.
# MAGIC AUTHOR. RISK-ADJUSTMENT-TEAM.
# MAGIC
# MAGIC DATA DIVISION.
# MAGIC WORKING-STORAGE SECTION.
# MAGIC 01  WS-MEMBER-ID       PIC X(10).
# MAGIC 01  WS-RISK-YEAR       PIC 9(4) VALUE 2023.
# MAGIC 01  WS-TOTAL-RISK      PIC 9(3)V999 VALUE 0.
# MAGIC 01  WS-MAX-RISK        PIC 9(3)V999 VALUE 0.
# MAGIC 01  WS-RISK-CATEGORY   PIC X(10).
# MAGIC
# MAGIC PROCEDURE DIVISION.
# MAGIC MAIN-SCORING.
# MAGIC     PERFORM READ-RISK-DATA
# MAGIC     PERFORM APPLY-HIERARCHIES
# MAGIC     PERFORM CALCULATE-MEMBER-RISK
# MAGIC     PERFORM CATEGORIZE-RISK
# MAGIC     PERFORM WRITE-SCORES
# MAGIC     STOP RUN.
# MAGIC
# MAGIC READ-RISK-DATA.
# MAGIC     * Read from PAYER-DEV.ANALYTICS-GOLD.RISK-SCORES
# MAGIC     * Filter WHERE RISK-YEAR = 2023
# MAGIC     * Include HCC codes and risk scores
# MAGIC     
# MAGIC APPLY-HIERARCHIES.
# MAGIC     * For each member, if hierarchical_flag = 1
# MAGIC     * Keep only the highest scoring HCC in disease group
# MAGIC     * Use window function: ROW_NUMBER() over member+disease_group
# MAGIC     
# MAGIC CALCULATE-MEMBER-RISK.
# MAGIC     * GROUP BY MEMBER-ID
# MAGIC     * SUM(RISK-SCORE) as TOTAL-RISK-SCORE
# MAGIC     * MAX(RISK-SCORE) as MAX-HCC-SCORE
# MAGIC     * COUNT(HCC-CODE) as HCC-COUNT
# MAGIC     
# MAGIC CATEGORIZE-RISK.
# MAGIC     * IF TOTAL-RISK-SCORE < 1.0 THEN 'Low Risk'
# MAGIC     * ELSE IF TOTAL-RISK-SCORE < 2.0 THEN 'Medium Risk'
# MAGIC     * ELSE 'High Risk'
# MAGIC     
# MAGIC WRITE-SCORES.
# MAGIC     * Write to PAYER-ANALYST-DEV.RISK-ADJUSTMENT.MEMBER-RISK-SCORES
# MAGIC ```

# COMMAND ----------

# 🎯 LIVE DEMO: Paste COBOL code here and invoke Assistant (Cmd+I)
#
# This example showcases:
# - Window functions (ROW_NUMBER)
# - Hierarchical logic
# - Aggregations
# - Case/When conditionals
#
# Expected: PySpark code with vikcbl_payer_dev → vikcbl_payer_analyst_dev

# [PASTE COBOL CODE HERE AND INVOKE ASSISTANT]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference: Expected Conversion with Window Functions
# MAGIC
# MAGIC ```python
# MAGIC from pyspark.sql import functions as F
# MAGIC from pyspark.sql.window import Window
# MAGIC
# MAGIC # Read risk scores
# MAGIC risk_df = spark.table(f"{SOURCE_CATALOG}.analytics_gold.risk_scores").filter(
# MAGIC     F.col("risk_year") == 2023
# MAGIC )
# MAGIC
# MAGIC # Apply hierarchies - keep highest score per disease group per member
# MAGIC window_spec = Window.partitionBy("member_id", "disease_group").orderBy(F.desc("risk_score"))
# MAGIC
# MAGIC hierarchical_df = risk_df.withColumn("rank", F.row_number().over(window_spec)).filter(
# MAGIC     (F.col("hierarchical_flag") == 0) | (F.col("rank") == 1)
# MAGIC ).drop("rank")
# MAGIC
# MAGIC # Calculate member-level risk scores
# MAGIC member_risk_df = hierarchical_df.groupBy("member_id").agg(
# MAGIC     F.sum("risk_score").alias("total_risk_score"),
# MAGIC     F.max("risk_score").alias("max_hcc_score"),
# MAGIC     F.count("hcc_code").alias("hcc_count")
# MAGIC )
# MAGIC
# MAGIC # Categorize risk
# MAGIC final_df = member_risk_df.withColumn(
# MAGIC     "risk_category",
# MAGIC     F.when(F.col("total_risk_score") < 1.0, "Low Risk")
# MAGIC      .when(F.col("total_risk_score") < 2.0, "Medium Risk")
# MAGIC      .otherwise("High Risk")
# MAGIC )
# MAGIC
# MAGIC # Write results
# MAGIC final_df.write.mode("overwrite").saveAsTable(
# MAGIC     f"{TARGET_CATALOG}.risk_adjustment.member_risk_scores"
# MAGIC )
# MAGIC
# MAGIC display(final_df)
# MAGIC ```

# COMMAND ----------


