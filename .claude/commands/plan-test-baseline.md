---
description: Run baseline test collection for PDF Reduce to Text project
allowed-tools: Bash(.*), TodoWrite, Read, Write, Edit
---

# Baseline Testing for PDF Reduce to Text

**Purpose**: Establish baseline before code changes
**Project**: PDF Context Window Stuffing Tool
**Note**: CLI tool with smoke tests in module __main__ blocks

---

## Project Configuration

**Identity**:
- **Prefix**: [PDF-REDUCE]
- **Project Name**: PDF Context Window Stuffing Tool
- **Working Directory**: /mnt/DATA01/include/www.deepily.ai/projects/pdf-reduce-to-text

**Paths**:
- **Logs Directory**: tests/results/logs
- **Reports Directory**: tests/results/reports

**Test Types**: smoke (module-level validation)

**Test Scripts** (smoke tests via module execution):
```bash
# Core component smoke tests
python -m src.auth_checker      # Google Cloud authentication validation
python -m src.gemini_client     # Gemini 2.5 Flash client testing
python -m src.pdf_processor     # PDF processing components
```

**Health Checks**: None required (CLI tool, no server dependencies)

**Environment**:
- Requires Google Cloud credentials
- Optional: PROJECT_ID environment variable
- Optional: Sample PDFs in data/input/ for full integration test

---

## Instructions to Claude

### 1. Read the Canonical Workflow

Read and execute: **planning-is-prompting → workflow/testing-baseline.md**

### 2. Apply Configuration

Use the project configuration above when executing the baseline workflow.

### 3. Test Execution

**For this project, "smoke tests" means**:
- Execute each core module's `quick_smoke_test()` function
- Validate module imports successfully
- Check basic functionality works
- Verify no import errors or configuration issues

**Test execution approach**:
```bash
# Run each module's smoke test
cd /mnt/DATA01/include/www.deepily.ai/projects/pdf-reduce-to-text

echo "=== PDF Reduce to Text - Smoke Test Baseline ==="

# Test 1: Auth Checker
echo "Testing authentication module..."
python -m src.auth_checker 2>&1 | tee tests/results/logs/auth_checker.log

# Test 2: Gemini Client
echo "Testing Gemini client module..."
python -m src.gemini_client 2>&1 | tee tests/results/logs/gemini_client.log

# Test 3: PDF Processor
echo "Testing PDF processor module..."
python -m src.pdf_processor 2>&1 | tee tests/results/logs/pdf_processor.log

echo ""
echo "Smoke test baseline complete."
```

### 4. Expected Outcome

**Baseline report should show**:
- Authentication module: ✅ (or ⚠️ if GCP credentials not configured)
- Gemini client: ✅ (or ⚠️ if API not accessible)
- PDF processor: ✅ (basic functionality)
- Overall health: GOOD or NEEDS_SETUP (depending on GCP configuration)

This baseline validates core components before making code changes.

---

**For subsequent baselines**: Run this before making code changes to establish known-good state.
