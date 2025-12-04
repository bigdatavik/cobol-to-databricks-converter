# Databricks notebook source
# MAGIC %md
# MAGIC # COBOL Demo 5: Provider Performance Dashboard (SQL)
# MAGIC **Objective**: Convert COBOL provider metrics batch job to Spark SQL
# MAGIC
# MAGIC **Demo Flow**:
# MAGIC 1. See legacy COBOL provider analytics code
# MAGIC 2. Copy and paste into empty cell
# MAGIC 3. Invoke Assistant to convert COBOL → Spark SQL with joins & aggregations

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
# MAGIC PROGRAM-ID. PROVIDER-PERFORMANCE-REPORT.
# MAGIC AUTHOR. NETWORK-ANALYTICS-TEAM.
# MAGIC
# MAGIC DATA DIVISION.
# MAGIC WORKING-STORAGE SECTION.
# MAGIC 01  WS-PROVIDER-ID     PIC X(10).
# MAGIC 01  WS-SPECIALTY       PIC X(30).
# MAGIC 01  WS-TOTAL-CLAIMS    PIC 9(7) VALUE 0.
# MAGIC 01  WS-PAID-CLAIMS     PIC 9(7) VALUE 0.
# MAGIC 01  WS-DENIED-CLAIMS   PIC 9(7) VALUE 0.
# MAGIC 01  WS-TOTAL-PAID-AMT  PIC 9(9)V99 VALUE 0.
# MAGIC 01  WS-AVG-PAID-AMT    PIC 9(7)V99 VALUE 0.
# MAGIC 01  WS-PAY-RATE-PCT    PIC 999V99.
# MAGIC
# MAGIC PROCEDURE DIVISION.
# MAGIC MAIN-ANALYSIS.
# MAGIC     PERFORM READ-DATA
# MAGIC     PERFORM CALCULATE-METRICS
# MAGIC     PERFORM RANK-PROVIDERS
# MAGIC     PERFORM WRITE-DASHBOARD
# MAGIC     STOP RUN.
# MAGIC
# MAGIC READ-DATA.
# MAGIC     * Read from PAYER-DEV.ANALYTICS-GOLD.CLAIMS
# MAGIC     * Join with PROVIDERS on PROVIDER-ID
# MAGIC     * Filter WHERE SERVICE-DATE >= '2023-01-01'
# MAGIC     
# MAGIC CALCULATE-METRICS.
# MAGIC     * GROUP BY PROVIDER-ID, PROVIDER-NAME, SPECIALTY
# MAGIC     * COUNT(*) as TOTAL-CLAIMS
# MAGIC     * COUNT(CASE WHEN CLAIM-STATUS='Paid' THEN 1 END) as PAID-CLAIMS
# MAGIC     * COUNT(CASE WHEN CLAIM-STATUS='Denied' THEN 1 END) as DENIED-CLAIMS
# MAGIC     * SUM(PAID-AMOUNT) as TOTAL-PAID-AMOUNT
# MAGIC     * AVG(PAID-AMOUNT) as AVG-PAID-AMOUNT
# MAGIC     * COMPUTE PAY-RATE-PCT = (PAID-CLAIMS / TOTAL-CLAIMS) * 100
# MAGIC     
# MAGIC RANK-PROVIDERS.
# MAGIC     * Order by TOTAL-PAID-AMOUNT DESC
# MAGIC     * Add RANK() window function by specialty
# MAGIC     
# MAGIC WRITE-DASHBOARD.
# MAGIC     * Write to PAYER-ANALYST-DEV.PROVIDER-ANALYTICS.PERFORMANCE-DASHBOARD
# MAGIC ```

# COMMAND ----------

# 🎯 LIVE DEMO: Paste COBOL code here and invoke Assistant (Cmd+I)
#
# This showcases:
# - Multi-table joins
# - Conditional aggregations (CASE WHEN)
# - Calculated metrics
# - Ranking with RANK()
#
# Expected: SQL query with vikcbl_payer_dev → vikcbl_payer_analyst_dev

# [PASTE COBOL CODE HERE AND INVOKE ASSISTANT]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Reference: Expected SQL Conversion
# MAGIC
# MAGIC ```sql
# MAGIC CREATE OR REPLACE TABLE {TARGET_CATALOG}.provider_analytics.performance_dashboard AS
# MAGIC WITH provider_metrics AS (
# MAGIC   SELECT 
# MAGIC     p.provider_id,
# MAGIC     p.provider_name,
# MAGIC     p.specialty,
# MAGIC     COUNT(*) as total_claims,
# MAGIC     SUM(CASE WHEN c.claim_status = 'Paid' THEN 1 ELSE 0 END) as paid_claims,
# MAGIC     SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END) as denied_claims,
# MAGIC     SUM(c.paid_amount) as total_paid_amount,
# MAGIC     AVG(c.paid_amount) as avg_paid_amount
# MAGIC   FROM {SOURCE_CATALOG}.analytics_gold.claims c
# MAGIC   INNER JOIN {SOURCE_CATALOG}.analytics_gold.providers p
# MAGIC     ON c.provider_id = p.provider_id
# MAGIC   WHERE c.service_date >= '2023-01-01'
# MAGIC   GROUP BY p.provider_id, p.provider_name, p.specialty
# MAGIC )
# MAGIC SELECT 
# MAGIC   *,
# MAGIC   ROUND((paid_claims / total_claims) * 100, 2) as pay_rate_pct,
# MAGIC   RANK() OVER (PARTITION BY specialty ORDER BY total_paid_amount DESC) as specialty_rank
# MAGIC FROM provider_metrics
# MAGIC ORDER BY total_paid_amount DESC;
# MAGIC
# MAGIC -- Display results
# MAGIC SELECT * FROM {TARGET_CATALOG}.provider_analytics.performance_dashboard
# MAGIC LIMIT 20;
# MAGIC ```

# COMMAND ----------


