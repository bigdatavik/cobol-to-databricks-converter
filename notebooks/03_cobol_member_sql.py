# Databricks notebook source
# MAGIC %md
# MAGIC # COBOL Demo 3: Member Analytics - Enrollment Trends (SQL)
# MAGIC **Objective**: Convert COBOL program to Spark SQL for member enrollment reporting
# MAGIC
# MAGIC **Demo Flow**:
# MAGIC 1. See legacy COBOL code below
# MAGIC 2. Copy and paste into empty cell
# MAGIC 3. Invoke Assistant to convert COBOL → Spark SQL

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
# MAGIC PROGRAM-ID. MEMBER-ENROLLMENT-TRENDS.
# MAGIC AUTHOR. ENROLLMENT-TEAM.
# MAGIC
# MAGIC DATA DIVISION.
# MAGIC WORKING-STORAGE SECTION.
# MAGIC 01  WS-ENROLLMENT-YEAR PIC 9(4).
# MAGIC 01  WS-ENROLLMENT-MONTH PIC 99.
# MAGIC 01  WS-PLAN-ID         PIC X(10).
# MAGIC 01  WS-MEMBER-COUNT    PIC 9(7) VALUE 0.
# MAGIC 01  WS-STATUS          PIC X(10) VALUE 'Active'.
# MAGIC
# MAGIC PROCEDURE DIVISION.
# MAGIC MAIN-REPORT.
# MAGIC     PERFORM READ-MEMBERS
# MAGIC     PERFORM CALCULATE-TRENDS
# MAGIC     PERFORM GENERATE-REPORT
# MAGIC     STOP RUN.
# MAGIC
# MAGIC READ-MEMBERS.
# MAGIC     * Read from PAYER-DEV.ANALYTICS-GOLD.MEMBERS
# MAGIC     * Filter WHERE MEMBER-STATUS = 'Active'
# MAGIC     * Extract YEAR and MONTH from ENROLLMENT-DATE
# MAGIC     
# MAGIC CALCULATE-TRENDS.
# MAGIC     * GROUP BY ENROLLMENT-YEAR, ENROLLMENT-MONTH, PLAN-ID
# MAGIC     * COUNT(MEMBER-ID) as NEW-ENROLLMENTS
# MAGIC     * Calculate running total within each plan
# MAGIC     * Order by ENROLLMENT-YEAR, ENROLLMENT-MONTH
# MAGIC     
# MAGIC GENERATE-REPORT.
# MAGIC     * Write to PAYER-ANALYST-DEV.MEMBER-ANALYTICS.ENROLLMENT-TRENDS
# MAGIC ```

# COMMAND ----------

# 🎯 LIVE DEMO: Paste COBOL code here and invoke Assistant (Cmd+I)
#
# Ask Assistant: "Convert this COBOL to Spark SQL using vikcbl catalogs"
#
# Expected output:
# - SQL query reading vikcbl_payer_dev.analytics_gold.members
# - Window functions for running totals
# - Creates view/table in vikcbl_payer_analyst_dev.member_analytics

# [PASTE COBOL CODE HERE AND INVOKE ASSISTANT]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference: Expected SQL Conversion
# MAGIC
# MAGIC ```sql
# MAGIC -- Create enrollment trends report
# MAGIC CREATE OR REPLACE TABLE {TARGET_CATALOG}.member_analytics.enrollment_trends AS
# MAGIC SELECT 
# MAGIC   YEAR(enrollment_date) as enrollment_year,
# MAGIC   MONTH(enrollment_date) as enrollment_month,
# MAGIC   plan_id,
# MAGIC   COUNT(member_id) as new_enrollments,
# MAGIC   SUM(COUNT(member_id)) OVER (
# MAGIC     PARTITION BY plan_id 
# MAGIC     ORDER BY YEAR(enrollment_date), MONTH(enrollment_date)
# MAGIC     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
# MAGIC   ) as cumulative_enrollments
# MAGIC FROM {SOURCE_CATALOG}.analytics_gold.members
# MAGIC WHERE member_status = 'Active'
# MAGIC GROUP BY 
# MAGIC   YEAR(enrollment_date), 
# MAGIC   MONTH(enrollment_date), 
# MAGIC   plan_id
# MAGIC ORDER BY 
# MAGIC   enrollment_year, 
# MAGIC   enrollment_month, 
# MAGIC   plan_id;
# MAGIC   
# MAGIC -- Display results
# MAGIC SELECT * FROM {TARGET_CATALOG}.member_analytics.enrollment_trends;
# MAGIC ```

# COMMAND ----------


