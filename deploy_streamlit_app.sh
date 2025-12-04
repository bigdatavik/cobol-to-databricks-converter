#!/bin/bash

# Quick update script for assistant instructions only
# Use this when you've ONLY changed .assistant_instructions.md
# This skips catalog/data recreation (much faster!)

set -e

#=============================================================================
# Configuration - Auto-detects current user
#=============================================================================
# Override profile by setting: export DATABRICKS_PROFILE="your_profile"
PROFILE=${DATABRICKS_PROFILE:-DEFAULT_azure}

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

#=============================================================================
# Read volume configuration from databricks.yml
#=============================================================================
echo "📋 Reading configuration from databricks.yml..."

SOURCE_CATALOG=$(grep -A2 "source_catalog:" databricks.yml | grep "default:" | awk '{print $2}' || echo "payer_dev")
TARGET_CATALOG=$(grep -A2 "target_catalog:" databricks.yml | grep "default:" | awk '{print $2}' || echo "payer_analyst_dev")
VOLUME_CATALOG=$(grep -A2 "volume_catalog:" databricks.yml | grep "default:" | awk '{print $2}' || echo "payer_dev")
VOLUME_SCHEMA=$(grep -A2 "volume_schema:" databricks.yml | grep "default:" | awk '{print $2}' || echo "sas_migration")
VOLUME_NAME=$(grep -A2 "volume_name:" databricks.yml | grep "default:" | awk '{print $2}' || echo "legacy_sas")

echo "   Source catalog: $SOURCE_CATALOG"
echo "   Target catalog: $TARGET_CATALOG"
echo "   Volume: $VOLUME_CATALOG.$VOLUME_SCHEMA.$VOLUME_NAME"
echo ""
#=============================================================================

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Quick Instructions Update - No Data Reload                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Step 0: Sync instructions from source to dashboard (CRITICAL!)
echo "🔄 Step 0/4: Syncing instructions from source to dashboard..."
cd "$PROJECT_DIR"
cp config/.assistant_instructions.md dashboard/config/.assistant_instructions.md
echo "✅ Synced: config/.assistant_instructions.md → dashboard/config/.assistant_instructions.md"
echo ""

# Step 1: Deploy bundle (uploads dashboard folder with synced instructions)
echo "📦 Step 1/4: Deploying bundle (uploads app with new instructions)..."
databricks bundle deploy --profile $PROFILE
echo "✅ Bundle deployed"
echo ""

# Step 2: Redeploy app (picks up new instructions)
echo "🚀 Step 2/4: Redeploying app..."
databricks apps deploy sas-converter \
  --source-code-path /Workspace/Users/$DATABRICKS_USER/.bundle/sas-payer-migration-demo/dev/files/dashboard \
  --profile $PROFILE
echo "✅ App redeployed"
echo ""

echo "🔐 Step 3/4: App permissions setup required..."

# Get app service principal UUID (client_id)
APP_NAME="sas-converter"
APP_JSON=$(databricks apps get $APP_NAME --profile $PROFILE --output json 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$APP_JSON" ]; then
    APP_SP_UUID=$(echo "$APP_JSON" | jq -r .service_principal_client_id 2>/dev/null || echo "$APP_JSON" | grep -o '"service_principal_client_id":"[^"]*"' | cut -d'"' -f4)
    APP_SP_NAME=$(echo "$APP_JSON" | jq -r .service_principal_name 2>/dev/null || echo "$APP_JSON" | grep -o '"service_principal_name":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$APP_SP_UUID" ]; then
        echo "✅ App deployed: $APP_SP_NAME"
        echo "   Service Principal UUID: $APP_SP_UUID"
        echo ""
        echo "📋 NEXT STEP: Grant permissions in SQL Editor"
        echo "   Run: ./show_grant_commands.sh"
        echo ""
        echo "   Or copy these commands to SQL Editor:"
        echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "   GRANT USE CATALOG ON CATALOG payer_dev TO \`$APP_SP_UUID\`;"
        echo "   GRANT USE SCHEMA ON SCHEMA payer_dev.sas_migration TO \`$APP_SP_UUID\`;"
        echo "   GRANT READ VOLUME ON VOLUME payer_dev.sas_migration.legacy_sas TO \`$APP_SP_UUID\`;"
        echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    else
        echo "⚠️  Could not detect service principal UUID"
    fi
else
    echo "⚠️  Could not get app information"
fi
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ DEPLOYMENT COMPLETE!                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Instructions file updated:"
echo "   Source: config/.assistant_instructions.md (1,704 lines)"
echo "   Deployed: dashboard/config/.assistant_instructions.md (synced)"
echo ""
echo "⏱️  Deployment time: ~30 seconds"
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  ACTION REQUIRED: Grant App Permissions (One-Time)         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🔐 The app needs permissions to access Unity Catalog volumes."
echo ""
echo "📋 Run these SQL commands in Databricks SQL Editor:"
echo ""
if [ -n "$APP_SP_UUID" ]; then
    echo "   GRANT USE CATALOG ON CATALOG payer_dev TO \`$APP_SP_UUID\`;"
    echo "   GRANT USE SCHEMA ON SCHEMA payer_dev.sas_migration TO \`$APP_SP_UUID\`;"
    echo "   GRANT READ VOLUME ON VOLUME payer_dev.sas_migration.legacy_sas TO \`$APP_SP_UUID\`;"
    echo "   GRANT SELECT ON CATALOG payer_dev TO \`$APP_SP_UUID\`;"
    echo ""
    echo "   💾 Commands saved to: grant_commands.sql"
    echo "   📖 Full list: ./show_grant_commands.sh"
else
    echo "   Run: ./show_grant_commands.sh"
fi
echo ""
echo "✅ After running these commands, refresh your app to use the volume!"
echo ""

