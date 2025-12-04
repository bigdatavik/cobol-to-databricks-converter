# Deployment Guide: Two Ways to Use the Framework

## 🎯 Overview

This framework supports two different use cases:
1. **Streamlit App** - Automated UI for batch conversions
2. **Databricks Assistant** - Manual conversions in notebooks with AI guidance

Each has its own deployment script.

---

## Option 1: Deploy Streamlit App

### Script: `./deploy_streamlit_app.sh`

**⏱️ Time:** ~30 seconds  
**Use for:** Deploying the web-based conversion app

**Use when:**
- ✅ Changed `.assistant_instructions.md`
- ✅ Changed app code (`sas_converter_app.py`, `utils.py`, etc.)
- ✅ Testing conversion patterns in the app
- ✅ Updating app dependencies

**What it does:**
1. ✅ Syncs instructions: `config/.assistant_instructions.md` → `dashboard/config/`
2. ✅ Deploys bundle (uploads app files)
3. ✅ Redeploys app (restarts with new code)
4. ⏩ **Skips data setup** (fast!)

**Quick Update:**
```bash
# Edit instructions or app code
vim config/.assistant_instructions.md

# Deploy app (30 seconds)
./deploy_streamlit_app.sh

# Refresh app in browser - done!
```

---

## Option 2: Setup Databricks Assistant

### Script: `./setup_databricks_assistant.sh`

**⏱️ Time:** ~10 minutes  
**Use for:** Setting up for manual notebook conversions with Databricks Assistant

**Use when:**
- ✅ First time setup
- ✅ Setting up demo environment
- ✅ Need fresh data for testing
- ✅ Want to use Databricks Assistant for conversions

**What it does:**
1. ✅ Validates bundle
2. ✅ Deploys bundle (notebooks, files)
3. ✅ **Deploys instructions to your workspace folder** (for Databricks Assistant)
4. ✅ **Drops and recreates catalogs** (payer_dev, payer_analyst_dev)
5. ✅ **Loads 29,000 rows of sample data**
6. ✅ Creates all schemas and tables

**Full Setup:**
```bash
# Setup everything for Databricks Assistant
./setup_databricks_assistant.sh

# Open any notebook, use Databricks Assistant
# Paste SAS code, ask: "Convert this to PySpark"
```

---

## 📋 Quick Decision Tree

```
What do you want to do?
├─ Use Streamlit App for conversions?
│  └─ Run: ./deploy_streamlit_app.sh  (30 seconds)
│
└─ Use Databricks Assistant in notebooks?
   └─ Run: ./setup_databricks_assistant.sh  (10 minutes, one-time setup)
```

---

## 💡 Understanding the Two Approaches

### Where Instructions Are Used

**Streamlit App** (`deploy_streamlit_app.sh`)
- Reads from: `dashboard/config/.assistant_instructions.md`
- Calls LLM directly with instructions embedded in prompts
- Users interact via web UI
- No manual prompting needed

**Databricks Assistant** (`setup_databricks_assistant.sh`)
- Reads from: `/Workspace/Users/{user}/.assistant_instructions.md`
- Databricks Assistant uses these instructions automatically
- Users work in notebooks, ask Assistant to convert
- Interactive, manual approach

**Key Point:** These are two independent ways to use the same conversion logic!

---

## 📝 Examples

### Example 1: Update App with New Conversion Pattern
```bash
# Edit config/.assistant_instructions.md
vim config/.assistant_instructions.md

# Deploy updated app (30 seconds)
./deploy_streamlit_app.sh

# Refresh app in browser - done!
```

### Example 2: Setup Fresh Demo Environment with Databricks Assistant
```bash
# Setup everything: data + notebooks + assistant instructions
./setup_databricks_assistant.sh

# Open notebooks, use Databricks Assistant to convert SAS
# Notebooks 01-08 show example conversions
```

### Example 3: Both App and Assistant
```bash
# Setup Assistant + demo data (one time)
./setup_databricks_assistant.sh

# Deploy/update the app (as needed)
./deploy_streamlit_app.sh

# Now you have both: app for automation, Assistant for manual work
```

---

## 🚀 Recommended Workflows

**Workflow 1: Developing the Streamlit App**
```bash
# 1. Edit instructions or app code
vim config/.assistant_instructions.md

# 2. Quick deploy (30 seconds)
./deploy_streamlit_app.sh

# 3. Test in app
# 4. Repeat steps 1-3 as needed
```

**Workflow 2: Setting Up for Demos**
```bash
# Full setup with data (one time)
./setup_databricks_assistant.sh

# Shows:
# - Notebooks 01-08 with SAS → PySpark/SQL conversions
# - Sample data for testing
# - Databricks Assistant configured
```

**Workflow 3: Production Deployment (Both Tools)**
```bash
# Setup backend (data + notebooks)
./setup_databricks_assistant.sh

# Deploy frontend (app)
./deploy_streamlit_app.sh

# Result: Full environment with both conversion methods
```

---

## ⚠️ Common Mistakes

**Mistake 1:** Running full setup when you just need to update the app
```bash
# ❌ SLOW - Takes 10 minutes, drops data
./setup_databricks_assistant.sh

# ✅ FAST - Takes 30 seconds, no data loss
./deploy_streamlit_app.sh
```

**Mistake 2:** Confusing which tool reads which instructions
```
# Streamlit App reads: dashboard/config/.assistant_instructions.md
# Databricks Assistant reads: /Workspace/Users/{user}/.assistant_instructions.md

# They're independent! Update the one you're using.
```

**Mistake 3:** Not understanding the two different use cases
```bash
# ❌ CONFUSED - Mixing the two approaches
"I ran setup_databricks_assistant.sh, why doesn't the app work?"

# ✅ CLEAR - They're separate tools
# For app: ./deploy_streamlit_app.sh
# For Assistant: ./setup_databricks_assistant.sh
```

---

## 📊 Performance Comparison

| Task | Full Setup | App Deploy | Difference |
|------|-----------|-----------|-------------|
| Validate bundle | 5s | 5s | Same |
| Deploy bundle | 10s | 10s | Same |
| Deploy instructions to workspace | 5s | ⏩ Skipped | +5s |
| Drop catalogs | 20s | ⏩ Skipped | +20s |
| Create catalogs/schemas | 30s | ⏩ Skipped | +30s |
| Load 29,000 rows data | 500s | ⏩ Skipped | +500s |
| Redeploy app | ⏩ N/A | 10s | +10s |
| **TOTAL** | **~10 min** | **~30 sec** | **20x faster** |

---

## 🎯 Summary

**Two Independent Tools:**
- `./deploy_streamlit_app.sh` - Deploys web UI for automated conversions (30 sec)
- `./setup_databricks_assistant.sh` - Sets up notebooks + data + Assistant (10 min)

**When to Use Each:**
- **App**: Quick iterations, testing patterns, self-service for users
- **Assistant**: Full demos, manual conversions, teaching/learning

**Pro Tip:** Run setup once, then iterate on the app with quick deploys!




