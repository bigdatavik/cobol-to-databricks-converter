#!/bin/bash

# COBOL to Databricks Payer Migration Demo
# One-Command Clean, Deploy & Setup Script

set -e  # Exit on error

#=============================================================================
# Configuration - Auto-detects current user
#=============================================================================
# Override profile by setting: export DATABRICKS_PROFILE="your_profile"
PROFILE=${DATABRICKS_PROFILE:-DEFAULT}

echo "🔧 Using Databricks profile: $PROFILE"
echo ""

# Auto-detect current Databricks user
echo "🔍 Detecting current Databricks user..."
if command -v jq &> /dev/null; then
    DATABRICKS_USER=$(databricks current-user me --profile $PROFILE --output json 2>/dev/null | jq -r .userName)
else
    # Fallback without jq (parse JSON manually)
    DATABRICKS_USER=$(databricks current-user me --profile $PROFILE 2>/dev/null | grep -o '"userName":"[^"]*"' | cut -d'"' -f4)
fi

# Verify user was detected
if [ -z "$DATABRICKS_USER" ]; then
    echo "❌ ERROR: Could not detect Databricks user."
    echo ""
    echo "Please ensure:"
    echo "  1. Databricks CLI is installed and configured"
    echo "  2. Profile '$PROFILE' exists in ~/.databrickscfg"
    echo "  3. You can run: databricks current-user me --profile $PROFILE"
    echo ""
    exit 1
fi

echo "✅ Detected user: $DATABRICKS_USER"
echo ""
#=============================================================================

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  COBOL to Databricks Payer Migration Demo - Reset & Deploy    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Change to project directory
cd "$(dirname "$0")"

echo "📁 Project directory: $(pwd)"
echo ""

# Step 1: Validate bundle
echo "🔍 Step 1/4: Validating bundle configuration..."
if databricks bundle validate --profile $PROFILE; then
    echo "✅ Bundle validation passed"
else
    echo "❌ Bundle validation failed"
    exit 1
fi
echo ""

# Step 2: Deploy bundle
echo "📦 Step 2/4: Deploying bundle to Databricks..."
if databricks bundle deploy --profile $PROFILE; then
    echo "✅ Bundle deployed successfully"
else
    echo "❌ Bundle deployment failed"
    exit 1
fi
echo ""

# Step 3: Deploy assistant instructions to user home directory
echo "📋 Step 3/4: Deploying assistant instructions to user home directory..."
if databricks workspace import --profile $PROFILE \
    --overwrite \
    --format AUTO \
    --file config/.assistant_instructions.md \
    /Workspace/Users/$DATABRICKS_USER/.assistant_instructions.md; then
    echo "✅ Assistant instructions deployed from config/ to /Workspace/Users/$DATABRICKS_USER/.assistant_instructions.md"
else
    echo "⚠️  Warning: Failed to deploy assistant instructions"
    echo "   You may need to manually upload config/.assistant_instructions.md"
fi
echo ""

# Step 4: Run setup (drops catalogs and recreates with data)
echo "🚀 Step 4/4: Running setup (DROP CASCADE + CREATE + LOAD DATA)..."
echo "   This will:"
echo "   - 🗑️  Drop existing payer_dev and payer_analyst_dev catalogs"
echo "   - 📦 Create fresh catalogs and schemas"
echo "   - 📊 Load 42,000 rows of sample data"
echo ""

if databricks bundle run setup_cobol_demo --profile $PROFILE; then
    echo ""
    
    # Detect the actual catalog name that was created (with dynamic user prefix)
    # Extract first name from email and add "cbl" suffix
    USER_PREFIX=$(echo "$DATABRICKS_USER" | cut -d'@' -f1 | cut -d'.' -f1 | tr '[:upper:]' '[:lower:]')
    ACTUAL_SOURCE_CATALOG="${USER_PREFIX}cbl_payer_dev"
    
    # Upload COBOL files to volume
    echo "📦 Uploading COBOL files to volume..."
    echo "   Target: $ACTUAL_SOURCE_CATALOG.cobol_migration.legacy_cobol"
    cd "$(dirname "$0")/legacy_cobol"
    UPLOAD_COUNT=0
    for file in *.cbl; do
        if databricks fs cp "$file" "dbfs:/Volumes/$ACTUAL_SOURCE_CATALOG/cobol_migration/legacy_cobol/$file" --profile $PROFILE --overwrite 2>/dev/null; then
            UPLOAD_COUNT=$((UPLOAD_COUNT + 1))
            echo "   ✓ $file"
        fi
    done
    echo "✅ Uploaded $UPLOAD_COUNT COBOL files to volume"
    cd -  > /dev/null
    echo ""
    
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                    ✅ SUCCESS!                                 ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 Catalogs created:"
    echo "   ✅ $ACTUAL_SOURCE_CATALOG (source - with 42,000 rows)"
    echo "   ✅ ${USER_PREFIX}cbl_payer_analyst_dev (target)"
    echo ""
    echo "📂 Schemas created:"
    echo "   Source: claims_bronze, claims_silver, analytics_gold, cobol_migration"
    echo "   Target: hedis_reports, risk_adjustment, claims_analytics,"
    echo "           provider_analytics, member_analytics, prior_auth_analytics"
    echo ""
    echo "📦 Volume created:"
    echo "   ✅ $ACTUAL_SOURCE_CATALOG.cobol_migration.legacy_cobol (with $UPLOAD_COUNT COBOL files)"
    echo ""
    echo "🎬 Ready to demo!"
    echo ""
    echo "🔗 Quick links:"
    echo "   Workspace: https://adb-984752964297111.11.azuredatabricks.net"
    echo "   Demo notebooks: /.bundle/cobol-migration-demo/dev/files/notebooks/"
    echo ""
    echo "📖 Next steps:"
    echo "   1. Open demo notebook: 01_cobol_hedis_pyspark"
    echo "   2. Test Assistant conversion with COBOL code"
    echo "   3. See DEMO_SCRIPT.md for full presentation guide"
    echo ""
else
    echo ""
    echo "❌ Setup failed"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "   1. Check cluster is running (Field Eng Shared UC LTS Cluster)"
    echo "   2. Verify Unity Catalog is enabled"
    echo "   3. Check job logs in Databricks UI"
    echo ""
    exit 1
fi

