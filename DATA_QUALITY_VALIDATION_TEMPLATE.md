# Data Quality Validation Template for SAS Instructions
# Add this section to your SAS assistant instructions file

---

## 🔍 STEP: DATA QUALITY VALIDATION (ALWAYS INCLUDE)

**CRITICAL**: After every conversion, ALWAYS add a validation step to ensure data quality and accuracy.

### Standard Validation Pattern:

```python
# ============================================================
# STEP: DATA QUALITY VALIDATION
# ============================================================

print("\n✅ DATA QUALITY CHECKS:")

# 1. Check for NULL values in critical columns
null_raf_count = member_raf_scores.filter(F.col("total_raf_score").isNull()).count()
print(f"   Members with NULL RAF scores: {null_raf_count,}")

# 2. Check for negative values (should not happen)
negative_raf_count = member_raf_scores.filter(F.col("total_raf_score") < 0).count()
print(f"   Members with negative RAF scores: {negative_raf_count,}")

# 3. Check for unrealistic values (business rule validation)
unrealistic_raf_count = member_raf_scores.filter(F.col("total_raf_score") > 10.0).count()
print(f"   Members with RAF > 10.0: {unrealistic_raf_count,}")

# 4. Verify all members were processed (reconciliation)
input_member_count = members_df.count()
output_member_count = member_raf_scores.count()
print(f"   Input members: {input_member_count,}")
print(f"   Output members: {output_member_count,}")
print(f"   Match: {'✅ YES' if input_member_count == output_member_count else '❌ NO'}")

# 5. Statistical summary
print("\n📊 RAF Score Statistics:")
member_raf_scores.select(
    F.min("total_raf_score").alias("min"),
    F.max("total_raf_score").alias("max"),
    F.avg("total_raf_score").alias("avg"),
    F.stddev("total_raf_score").alias("stddev")
).show()

# 6. Check for duplicates (if applicable)
duplicate_count = member_raf_scores.groupBy("member_id").count().filter(F.col("count") > 1).count()
print(f"   Duplicate member_ids: {duplicate_count}")

# Optional: Fail fast if critical issues found
assert null_raf_count == 0, "VALIDATION FAILED: NULL RAF scores found"
assert negative_raf_count == 0, "VALIDATION FAILED: Negative RAF scores found"
assert input_member_count == output_member_count, "VALIDATION FAILED: Member count mismatch"
```

---

## 📋 VALIDATION CHECKLIST (Include Relevant Ones)

### For Claims Processing:
```python
# Validate claim amounts
print("💰 CLAIMS VALIDATION:")

# Check for NULL amounts
null_amounts = claims_df.filter(F.col("claim_amount").isNull()).count()
print(f"   Claims with NULL amounts: {null_amounts}")

# Check for negative amounts
negative_amounts = claims_df.filter(F.col("claim_amount") < 0).count()
print(f"   Claims with negative amounts: {negative_amounts}")

# Check for unrealistic amounts (e.g., > $1M per claim)
high_amounts = claims_df.filter(F.col("claim_amount") > 1000000).count()
print(f"   Claims > $1M: {high_amounts}")

# Financial reconciliation
input_total = input_claims_df.agg(F.sum("claim_amount")).collect()[0][0]
output_total = claims_df.agg(F.sum("claim_amount")).collect()[0][0]
difference = abs(input_total - output_total) if input_total and output_total else 0

print(f"   Input total: ${input_total:,.2f}")
print(f"   Output total: ${output_total:,.2f}")
print(f"   Difference: ${difference:,.2f}")
assert difference < 0.01, f"Financial reconciliation failed: ${difference:,.2f}"
```

### For HEDIS/Quality Measures:
```python
# Validate HEDIS metrics
print("📊 HEDIS VALIDATION:")

# Check denominator and numerator logic
invalid_rates = hedis_df.filter(F.col("numerator") > F.col("denominator")).count()
print(f"   Invalid rates (num > denom): {invalid_rates}")

# Check for compliance rates > 100%
high_compliance = hedis_df.filter(F.col("compliance_pct") > 100).count()
print(f"   Compliance > 100%: {high_compliance}")

# Check for required exclusions
missing_exclusions = hedis_df.filter(F.col("exclusion").isNull()).count()
print(f"   Missing exclusion flags: {missing_exclusions}")

# Validate measure year
invalid_years = hedis_df.filter(
    ~F.col("measure_year").between(2020, 2025)
).count()
print(f"   Invalid measure years: {invalid_years}")
```

### For Member/Enrollment Data:
```python
# Validate member data
print("👥 MEMBER VALIDATION:")

# Check for NULL member IDs
null_ids = members_df.filter(F.col("member_id").isNull()).count()
print(f"   NULL member IDs: {null_ids}")

# Check for duplicate member IDs
duplicate_members = members_df.groupBy("member_id").count() \
    .filter(F.col("count") > 1).count()
print(f"   Duplicate member IDs: {duplicate_members}")

# Check for invalid ages
invalid_ages = members_df.filter(
    (F.col("age") < 0) | (F.col("age") > 120)
).count()
print(f"   Invalid ages: {invalid_ages}")

# Check enrollment status consistency
invalid_status = members_df.filter(
    (F.col("enrollment_status") == "ACTIVE") & 
    (F.col("termination_date").isNotNull())
).count()
print(f"   Active with termination date: {invalid_status}")
```

### For Date Fields:
```python
# Validate dates
print("📅 DATE VALIDATION:")

# Check for NULL dates in required fields
null_dates = df.filter(F.col("service_date").isNull()).count()
print(f"   NULL service dates: {null_dates}")

# Check for future dates (if not allowed)
future_dates = df.filter(F.col("service_date") > F.current_date()).count()
print(f"   Future dates: {future_dates}")

# Check for invalid date ranges
invalid_ranges = df.filter(
    F.col("start_date") > F.col("end_date")
).count()
print(f"   Invalid date ranges: {invalid_ranges}")

# Check for dates outside expected range (e.g., last 5 years)
old_dates = df.filter(
    F.col("service_date") < F.add_months(F.current_date(), -60)
).count()
print(f"   Dates older than 5 years: {old_dates}")
```

### Generic NULL Check Pattern:
```python
# Check for NULLs across all columns
print("🔍 NULL CHECK ACROSS ALL COLUMNS:")

null_counts = df.select([
    F.sum(F.when(F.col(c).isNull(), 1).otherwise(0)).alias(c)
    for c in df.columns
])

# Display columns with NULL values
null_summary = null_counts.collect()[0].asDict()
for col, count in null_summary.items():
    if count > 0:
        print(f"   {col}: {count} nulls")
```

---

## 🎯 WHEN TO USE EACH VALIDATION

| Validation Type | Use Case |
|----------------|----------|
| NULL checks | **Always** - for all critical columns |
| Negative values | Financial amounts, counts, ages |
| Range checks | RAF scores, compliance rates, ages |
| Duplicates | Member IDs, unique identifiers |
| Count reconciliation | **Always** - input vs output counts |
| Financial reconciliation | Claims, premiums, any monetary calculations |
| Date validation | Service dates, enrollment dates |
| Referential integrity | Foreign key relationships |

---

## 💡 BEST PRACTICES

1. **Always add validation as a separate step** - Don't mix with transformation logic
2. **Print clear messages** - Use emojis and formatting for visibility
3. **Use assertions for critical failures** - Fail fast on data quality issues
4. **Log statistics** - Min/max/avg/count for key metrics
5. **Compare input vs output** - Ensure no data loss during processing
6. **Document expected ranges** - Add comments for business rules
7. **Make it visual** - Use display() or show() for DataFrames when helpful

---

## 🚨 CRITICAL VALIDATIONS (NEVER SKIP)

```python
# These 4 checks should appear in EVERY conversion:

# 1. Record count reconciliation
assert input_count == output_count, f"Record count mismatch: {input_count} → {output_count}"

# 2. NULL check on primary key
assert df.filter(F.col("primary_key").isNull()).count() == 0, "NULL primary keys found"

# 3. Duplicate check on primary key
assert df.groupBy("primary_key").count().filter(F.col("count") > 1).count() == 0, "Duplicates found"

# 4. Financial reconciliation (for monetary calculations)
assert abs(input_total - output_total) < 0.01, f"Amount mismatch: ${input_total} → ${output_total}"
```

---


