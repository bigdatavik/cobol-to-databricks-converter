# Databricks notebook source
# MAGIC %md
# MAGIC # Setup: Create COBOL Migration Catalogs and Generate Sample Data
# MAGIC This notebook creates the complete Unity Catalog environment for COBOL-to-PySpark migration demos.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import *
from datetime import datetime, timedelta
import random

# Configuration - Get from job parameters (set by databricks.yml)
# Extract user prefix with "cbl" suffix for COBOL
current_user = spark.sql("SELECT current_user() as user").collect()[0]["user"]
user_prefix = current_user.split('@')[0].split('.')[0].lower() + "cbl"

# Create widgets with dynamic defaults (e.g., vikcbl for vik.malhotra)
dbutils.widgets.text("source_catalog", f"{user_prefix}_payer_dev")
dbutils.widgets.text("target_catalog", f"{user_prefix}_payer_analyst_dev")

SOURCE_CATALOG = dbutils.widgets.get("source_catalog")
TARGET_CATALOG = dbutils.widgets.get("target_catalog")

print(f"✅ Source Catalog (COBOL): {SOURCE_CATALOG}")
print(f"✅ Target Catalog (COBOL): {TARGET_CATALOG}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Clean Up Existing Catalogs (Idempotent Setup)

# COMMAND ----------

print("="*80)
print("🧹 CLEANING UP EXISTING COBOL CATALOGS (if any)")
print("="*80)

# Drop existing catalogs with CASCADE to remove all schemas and tables
try:
    spark.sql(f"DROP CATALOG IF EXISTS {SOURCE_CATALOG} CASCADE")
    print(f"🗑️  Dropped catalog: {SOURCE_CATALOG}")
except Exception as e:
    print(f"ℹ️  Catalog {SOURCE_CATALOG} doesn't exist or already dropped: {e}")

try:
    spark.sql(f"DROP CATALOG IF EXISTS {TARGET_CATALOG} CASCADE")
    print(f"🗑️  Dropped catalog: {TARGET_CATALOG}")
except Exception as e:
    print(f"ℹ️  Catalog {TARGET_CATALOG} doesn't exist or already dropped: {e}")

print("✅ Cleanup complete - ready for fresh COBOL setup\n")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Catalogs

# COMMAND ----------

print(f"📦 Creating catalog: {SOURCE_CATALOG}")
spark.sql(f"CREATE CATALOG {SOURCE_CATALOG}")
print(f"✅ {SOURCE_CATALOG} created")

print(f"📦 Creating catalog: {TARGET_CATALOG}")
spark.sql(f"CREATE CATALOG {TARGET_CATALOG}")
print(f"✅ {TARGET_CATALOG} created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2.5: Verify Catalog Ownership

# COMMAND ----------

# Get current user - they are automatically the owner of catalogs they create
current_user = spark.sql("SELECT current_user() as user").collect()[0]["user"]

print(f"👤 Current user: {current_user}")
print(f"✅ {current_user} is the owner of newly created COBOL catalogs")
print(f"   - {SOURCE_CATALOG}")
print(f"   - {TARGET_CATALOG}")
print()
print("📝 As catalog owner, you can grant permissions to other principals via:")
print("   - SQL: GRANT USE CATALOG ON CATALOG ... TO `principal`")
print("   - SDK: w.grants.update(...)")
print("   - Automated: setup_databricks_assistant.sh runs permission grant automatically")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create Schemas

# COMMAND ----------

print("📂 Creating schemas in source catalog...")
# Source schemas (including cobol_migration for volumes)
for schema in ["claims_bronze", "claims_silver", "analytics_gold", "cobol_migration"]:
    spark.sql(f"CREATE SCHEMA {SOURCE_CATALOG}.{schema}")
    print(f"✅ {SOURCE_CATALOG}.{schema}")

print("\n📂 Creating schemas in target catalog...")
# Target schemas (where COBOL conversions will write results)
for schema in ["hedis_reports", "risk_adjustment", "claims_analytics", "provider_analytics", "member_analytics", "prior_auth_analytics"]:
    spark.sql(f"CREATE SCHEMA {TARGET_CATALOG}.{schema}")
    print(f"✅ {TARGET_CATALOG}.{schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Create Volume for COBOL Files

# COMMAND ----------

print(f"📦 Creating volume for COBOL files...")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {SOURCE_CATALOG}.cobol_migration.legacy_cobol")
print(f"✅ Volume created: {SOURCE_CATALOG}.cobol_migration.legacy_cobol")
print(f"📍 Path: /Volumes/{SOURCE_CATALOG}/cobol_migration/legacy_cobol")
print()
print("📝 COBOL files (.cbl) will be uploaded here by setup script")
print("   Files: hedis_reports.cbl, claims_analytics.cbl, member_analytics.cbl,")
print("          risk_adjustment.cbl, provider_analytics.cbl, prior_auth_analytics.cbl")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Generate Sample Data (Simulating Mainframe Data)

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.1 Generate HEDIS Measures Data

# COMMAND ----------

print("📊 Generating HEDIS measures data...")

# Generate 5,000 HEDIS measure records
hedis_data = []
measure_ids = ['BCS', 'COL', 'CBP', 'CDC', 'HBD', 'CIS', 'W15', 'W30']
age_groups = ['50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84']

for i in range(5000):
    hedis_data.append({
        'measure_id': random.choice(measure_ids),
        'member_id': f'M{100000 + i}',
        'age': random.randint(50, 84),
        'age_group': random.choice(age_groups),
        'measure_year': random.choice([2022, 2023]),
        'numerator': random.choice([0, 1]),
        'denominator': 1,
        'exclusion': random.choice([0, 0, 0, 1]),  # 25% exclusions
        'service_date': (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 364))).strftime('%Y-%m-%d')
    })

hedis_df = spark.createDataFrame(hedis_data)
hedis_df.write.mode("overwrite").saveAsTable(f"{SOURCE_CATALOG}.analytics_gold.hedis_measures")
print(f"✅ Created {SOURCE_CATALOG}.analytics_gold.hedis_measures (5,000 rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.2 Generate Members Data

# COMMAND ----------

print("📊 Generating members data...")

members_data = []
for i in range(10000):
    birth_year = random.randint(1940, 2000)
    age = 2023 - birth_year
    gender = random.choice(['M', 'F'])
    
    # Calculate age_sex_factor (simplified CMS RAF model)
    if gender == 'M':
        if age >= 85:
            age_sex_factor = 1.4500
        elif age >= 75:
            age_sex_factor = 1.2500
        elif age >= 65:
            age_sex_factor = 1.0500
        elif age >= 55:
            age_sex_factor = 0.8500
        else:
            age_sex_factor = 0.7500
    else:  # Female
        if age >= 85:
            age_sex_factor = 1.3800
        elif age >= 75:
            age_sex_factor = 1.1900
        elif age >= 65:
            age_sex_factor = 1.0000
        elif age >= 55:
            age_sex_factor = 0.8100
        else:
            age_sex_factor = 0.7200
    
    enrollment_date = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1095))
    enrollment_months = random.randint(1, 36)  # months enrolled
    terminated = random.choice([False, False, False, True])  # 25% terminated
    termination_date = None if not terminated else (enrollment_date + timedelta(days=random.randint(30, 1095))).strftime('%Y-%m-%d')
    
    members_data.append({
        'member_id': f'M{100000 + i}',
        'first_name': f'FirstName{i}',
        'last_name': f'LastName{i}',
        'date_of_birth': f'{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}',
        'age': age,
        'gender': gender,
        'age_sex_factor': age_sex_factor,
        'zip_code': f'{random.randint(10000, 99999)}',
        'enrollment_date': enrollment_date.strftime('%Y-%m-%d'),
        'termination_date': termination_date,
        'enrollment_status': 'TERMINATED' if terminated else 'ACTIVE',
        'enrollment_months': enrollment_months,
        'plan_id': f'PLAN{random.randint(1, 5)}',
        'plan_type': random.choice(['MEDICARE', 'MEDICARE-ADVANTAGE', 'COMMERCIAL', 'INDIVIDUAL', 'GROUP']),
        'premium_amount': round(random.uniform(100, 800), 2),
        'claims_last_year': random.randint(0, 50),
        'total_cost_last_yr': round(random.uniform(0, 100000), 2),
        'member_status': 'TERMINATED' if terminated else 'ACTIVE',
        'disabled_flag': random.choice([0, 0, 0, 1]),
        'original_entitled': random.choice(['Age', 'Age', 'Disability', 'ESRD'])
    })

members_df = spark.createDataFrame(members_data)
members_df.write.mode("overwrite").saveAsTable(f"{SOURCE_CATALOG}.analytics_gold.members")
print(f"✅ Created {SOURCE_CATALOG}.analytics_gold.members (10,000 rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.3 Generate Claims Data

# COMMAND ----------

print("📊 Generating claims data...")

claims_data = []
procedure_codes = ['99213', '99214', '99215', '81000', '85025', '80053', '99232', '99233', '70450', '73060']
diagnosis_codes = ['E11.9', 'I10', 'J44.9', 'K21.9', 'M19.90', 'F41.9', 'E78.5']

for i in range(8000):
    service_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 364))
    paid_date = service_date + timedelta(days=random.randint(10, 45))
    claim_status = random.choice(['Paid', 'Paid', 'Paid', 'Denied', 'Pending', 'APPROVED', 'PARTIAL'])
    billed_amount = round(random.uniform(50, 5000), 2)
    
    if claim_status in ['Paid', 'APPROVED']:
        paid_amount = round(billed_amount * random.uniform(0.8, 1.0), 2)
        denied_amount = 0.0
    elif claim_status == 'PARTIAL':
        paid_amount = round(billed_amount * random.uniform(0.3, 0.7), 2)
        denied_amount = billed_amount - paid_amount
    else:  # Denied or Pending
        paid_amount = 0.0
        denied_amount = billed_amount if claim_status == 'Denied' else 0.0
    
    claims_data.append({
        'claim_id': f'CLM{200000 + i}',
        'member_id': f'M{100000 + random.randint(0, 9999)}',
        'provider_id': f'PRV{random.randint(1000, 1100)}',
        'service_date': service_date.strftime('%Y-%m-%d'),
        'paid_date': paid_date.strftime('%Y-%m-%d'),
        'procedure_code': random.choice(procedure_codes),
        'diagnosis_code': random.choice(diagnosis_codes),
        'billed_amount': billed_amount,
        'claim_amount': billed_amount,  # alias
        'paid_amount': paid_amount,
        'denied_amount': denied_amount,
        'claim_status': claim_status,
        'claim_type': random.choice(['Professional', 'Institutional', 'Pharmacy']),
        'quality_score': random.randint(70, 100)
    })

claims_df = spark.createDataFrame(claims_data)
claims_df.write.mode("overwrite").saveAsTable(f"{SOURCE_CATALOG}.analytics_gold.claims")
print(f"✅ Created {SOURCE_CATALOG}.analytics_gold.claims (8,000 rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.4 Generate Providers Data

# COMMAND ----------

print("📊 Generating providers data...")

providers_data = []
specialties = ['Internal Medicine', 'Family Practice', 'Cardiology', 'Endocrinology', 'Orthopedics', 
               'Radiology', 'Pediatrics', 'Psychiatry', 'Dermatology']
provider_types = ['PCP', 'Specialist', 'Hospital', 'Lab', 'Imaging Center']

for i in range(100):
    providers_data.append({
        'provider_id': f'PRV{1000 + i}',
        'provider_name': f'Dr. Provider {i}',
        'provider_type': random.choice(provider_types),
        'specialty': random.choice(specialties),
        'npi': f'{1000000000 + i}',
        'address': f'{random.randint(100, 9999)} Main St',
        'city': random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']),
        'state': random.choice(['NY', 'CA', 'IL', 'TX', 'AZ']),
        'zip_code': f'{random.randint(10000, 99999)}',
        'network_status': random.choice(['In Network', 'In Network', 'Out of Network']),
        'contract_rate': round(random.uniform(80, 120), 2)  # percentage of billed charges
    })

providers_df = spark.createDataFrame(providers_data)
providers_df.write.mode("overwrite").saveAsTable(f"{SOURCE_CATALOG}.analytics_gold.providers")
print(f"✅ Created {SOURCE_CATALOG}.analytics_gold.providers (100 rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.5 Generate Risk Scores Data

# COMMAND ----------

print("📊 Generating risk scores data...")

risk_data = []
for i in range(6000):
    risk_data.append({
        'member_id': f'M{100000 + random.randint(0, 9999)}',
        'risk_year': random.choice([2022, 2023]),
        'hcc_code': f'HCC{random.randint(1, 189)}',
        'risk_score': round(random.uniform(0.5, 3.5), 3),
        'disease_group': random.choice(['Diabetes', 'Heart Disease', 'COPD', 'Cancer', 'Kidney Disease']),
        'hierarchical_flag': random.choice([0, 1])
    })

risk_df = spark.createDataFrame(risk_data)
risk_df.write.mode("overwrite").saveAsTable(f"{SOURCE_CATALOG}.analytics_gold.risk_scores")
print(f"✅ Created {SOURCE_CATALOG}.analytics_gold.risk_scores (6,000 rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.6 Generate Diagnoses Data (for Risk Adjustment)

# COMMAND ----------

print("📊 Generating diagnoses data...")

# HCC codes and their weights
hcc_codes = {
    'HCC17': {'weight': 0.302, 'description': 'Diabetes with Acute Complications'},
    'HCC18': {'weight': 0.318, 'description': 'Diabetes with Chronic Complications'},
    'HCC19': {'weight': 0.368, 'description': 'Diabetes without Complication'},
    'HCC85': {'weight': 0.323, 'description': 'Congestive Heart Failure'},
    'HCC86': {'weight': 0.189, 'description': 'Acute Myocardial Infarction'},
    'HCC87': {'weight': 0.271, 'description': 'Unstable Angina'},
    'HCC88': {'weight': 0.195, 'description': 'Angina Pectoris'},
    'HCC111': {'weight': 0.484, 'description': 'Chronic Obstructive Pulmonary Disease'},
    'HCC112': {'weight': 0.341, 'description': 'Fibrosis of Lung'},
}

diagnoses_data = []
for i in range(8000):
    hcc = random.choice(list(hcc_codes.keys()))
    diagnoses_data.append({
        'member_id': f'M{100000 + random.randint(0, 9999)}',
        'service_date': (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 364))).strftime('%Y-%m-%d'),
        'hcc_code': hcc,
        'hcc_weight': hcc_codes[hcc]['weight'],
        'diagnosis_description': hcc_codes[hcc]['description'],
        'has_diabetes': 1 if hcc in ['HCC17', 'HCC18', 'HCC19'] else 0,
        'has_chf': 1 if hcc == 'HCC85' else 0
    })

diagnoses_df = spark.createDataFrame(diagnoses_data)
diagnoses_df.write.mode("overwrite").saveAsTable(f"{SOURCE_CATALOG}.analytics_gold.diagnoses")
print(f"✅ Created {SOURCE_CATALOG}.analytics_gold.diagnoses (8,000 rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 5.7 Generate Prior Authorization Data

# COMMAND ----------

print("📊 Generating prior authorization data...")

prior_auth_data = []
auth_statuses = ['APPROVED', 'APPROVED', 'APPROVED', 'DENIED', 'PENDING']
reviewers = ['REV001', 'REV002', 'REV003', 'REV004', 'REV005']

for i in range(5000):
    request_date = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 334))
    auth_status = random.choice(auth_statuses)
    
    # Calculate approval date based on status
    if auth_status == 'APPROVED':
        turnaround_days = random.randint(1, 10)
        approval_date = (request_date + timedelta(days=turnaround_days)).strftime('%Y-%m-%d')
    elif auth_status == 'DENIED':
        turnaround_days = random.randint(1, 14)
        approval_date = (request_date + timedelta(days=turnaround_days)).strftime('%Y-%m-%d')
    else:  # PENDING
        approval_date = None
    
    prior_auth_data.append({
        'auth_id': f'AUTH{300000 + i}',
        'member_id': f'M{100000 + random.randint(0, 9999)}',
        'provider_id': f'PRV{random.randint(1000, 1100)}',
        'request_date': request_date.strftime('%Y-%m-%d'),
        'approval_date': approval_date,
        'auth_status': auth_status,
        'procedure_code': random.choice(['99213', '99214', '99215', '77067', '70450', '73060']),
        'diagnosis_code': random.choice(['E11.9', 'I10', 'J44.9', 'K21.9', 'M19.90']),
        'auth_amount': round(random.uniform(100, 50000), 2),
        'reviewer_id': random.choice(reviewers)
    })

prior_auth_df = spark.createDataFrame(prior_auth_data)
prior_auth_df.write.mode("overwrite").saveAsTable(f"{SOURCE_CATALOG}.analytics_gold.prior_auth_summary")
print(f"✅ Created {SOURCE_CATALOG}.analytics_gold.prior_auth_summary (5,000 rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Verify Data Loaded

# COMMAND ----------

print("="*80)
print("📊 SUMMARY: COBOL Migration Environment Created")
print("="*80)
print()

print(f"✅ Catalogs:")
print(f"   - {SOURCE_CATALOG} (source)")
print(f"   - {TARGET_CATALOG} (target)")
print()

print(f"✅ Schemas in {SOURCE_CATALOG}:")
print(f"   - claims_bronze")
print(f"   - claims_silver")
print(f"   - analytics_gold")
print(f"   - cobol_migration")
print()

print(f"✅ Volume:")
print(f"   - {SOURCE_CATALOG}.cobol_migration.legacy_cobol")
print()

print(f"✅ Sample tables in {SOURCE_CATALOG}.analytics_gold:")
tables = [
    ('hedis_measures', 5000),
    ('members', 10000),
    ('claims', 8000),
    ('providers', 100),
    ('risk_scores', 6000),
    ('diagnoses', 8000),
    ('prior_auth_summary', 5000)
]

total_rows = 0
for table, expected_rows in tables:
    actual_rows = spark.table(f"{SOURCE_CATALOG}.analytics_gold.{table}").count()
    print(f"   - {table}: {actual_rows:,} rows")
    total_rows += actual_rows

print()
print(f"📊 Total rows: {total_rows:,}")
print()

print(f"✅ Schemas in {TARGET_CATALOG} (ready for COBOL conversions):")
print(f"   - hedis_reports")
print(f"   - risk_adjustment")
print(f"   - claims_analytics")
print(f"   - provider_analytics")
print(f"   - member_analytics")
print(f"   - prior_auth_analytics")
print()

print("="*80)
print("✅ COBOL MIGRATION ENVIRONMENT READY!")
print("="*80)
print()
print("🎯 Next steps:")
print("   1. Upload COBOL files to volume (done by setup script)")
print("   2. Open demo notebook: 01_cobol_hedis_pyspark")
print("   3. Copy COBOL code from markdown cell")
print("   4. Paste into empty cell and invoke Databricks Assistant")
print("   5. Watch AI convert COBOL → PySpark using instructions!")

# COMMAND ----------

