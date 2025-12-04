#!/bin/bash

# Helper script: Shows the exact SQL commands to grant app permissions
# Run this after deploying the app

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  App Permission Grant Commands                                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Get the app service principal
APP_NAME="sas-converter"
PROFILE="${DATABRICKS_PROFILE:-DEFAULT_azure}"

echo "🔍 Getting app service principal..."

APP_JSON=$(databricks apps get $APP_NAME --profile $PROFILE --output json 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$APP_JSON" ]; then
    echo "❌ Error: Could not find app '$APP_NAME'"
    echo "   Make sure the app is deployed first: ./deploy_streamlit_app.sh"
    exit 1
fi

# Get service principal UUID (client_id) - this is what grants need!
APP_SP_UUID=$(echo "$APP_JSON" | jq -r .service_principal_client_id 2>/dev/null || echo "$APP_JSON" | grep -o '"service_principal_client_id":"[^"]*"' | cut -d'"' -f4)
APP_SP_NAME=$(echo "$APP_JSON" | jq -r .service_principal_name 2>/dev/null || echo "$APP_JSON" | grep -o '"service_principal_name":"[^"]*"' | cut -d'"' -f4)

if [ -z "$APP_SP_UUID" ]; then
    echo "❌ Error: Could not detect service principal UUID"
    exit 1
fi

echo "✅ App: $APP_NAME"
echo "✅ Service Principal: $APP_SP_NAME"
echo "✅ Service Principal UUID: $APP_SP_UUID"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "📋 Copy and run these commands in Databricks SQL Editor:"
echo "═══════════════════════════════════════════════════════════════"
echo ""
cat << EOF
-- Grant permissions to app: $APP_SP_NAME
-- Service Principal UUID: $APP_SP_UUID

-- Volume access (required for browsing SAS files)
GRANT USE CATALOG ON CATALOG payer_dev TO \`$APP_SP_UUID\`;
GRANT USE SCHEMA ON SCHEMA payer_dev.sas_migration TO \`$APP_SP_UUID\`;
GRANT READ VOLUME ON VOLUME payer_dev.sas_migration.legacy_sas TO \`$APP_SP_UUID\`;

-- Data access (optional - for preview features)
GRANT SELECT ON CATALOG payer_dev TO \`$APP_SP_UUID\`;
GRANT USE CATALOG ON CATALOG payer_analyst_dev TO \`$APP_SP_UUID\`;
GRANT SELECT ON CATALOG payer_analyst_dev TO \`$APP_SP_UUID\`;

-- Verify the grants
SHOW GRANTS ON VOLUME payer_dev.sas_migration.legacy_sas;
EOF
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "💡 These commands are also saved to: grant_commands.sql"
echo ""

# Save to file
cat > grant_commands.sql << EOF
-- Grant permissions to app: $APP_SP_NAME
-- Service Principal UUID: $APP_SP_UUID
-- Generated: $(date)

-- Volume access (required for browsing SAS files)
GRANT USE CATALOG ON CATALOG payer_dev TO \`$APP_SP_UUID\`;
GRANT USE SCHEMA ON SCHEMA payer_dev.sas_migration TO \`$APP_SP_UUID\`;
GRANT READ VOLUME ON VOLUME payer_dev.sas_migration.legacy_sas TO \`$APP_SP_UUID\`;

-- Data access (optional - for preview features)
GRANT SELECT ON CATALOG payer_dev TO \`$APP_SP_UUID\`;
GRANT USE CATALOG ON CATALOG payer_analyst_dev TO \`$APP_SP_UUID\`;
GRANT SELECT ON CATALOG payer_analyst_dev TO \`$APP_SP_UUID\`;

-- Verify the grants
SHOW GRANTS ON VOLUME payer_dev.sas_migration.legacy_sas;
EOF

echo "✅ Done! Run these commands in SQL Editor to grant permissions."
echo ""

