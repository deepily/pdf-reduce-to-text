---
description: Run post-change verification for PDF Reduce to Text project
allowed-tools: Bash(.*), TodoWrite, Read, Write, Edit, Grep, Glob
arguments:
  - name: baseline_report
    description: Path to baseline report (auto-detects if not provided)
    required: false
  - name: scope
    description: Remediation scope (FULL|CRITICAL_ONLY|SELECTIVE|ANALYSIS_ONLY)
    required: false
    default: FULL
---

# Post-Change Remediation for PDF Reduce to Text

**Purpose**: Verify core components after code changes
**Project**: PDF Context Window Stuffing Tool
**Note**: Fixes failing smoke tests and validates component integrity

---

## Project Configuration

**Identity**:
- **Prefix**: [PDF-REDUCE]
- **Project Name**: PDF Context Window Stuffing Tool
- **Working Directory**: /mnt/DATA01/include/www.deepily.ai/projects/pdf-reduce-to-text

**Arguments**:
- **Baseline Report**: ${1:-auto}
- **Remediation Scope**: ${2:-FULL}

**Baseline Auto-Detection**:
- **Directory**: tests/results/reports
- **Pattern**: *baseline-test-report.md
- **Sort**: Most recent timestamp

**Test Configuration** (same as baseline):
- **Test Types**: smoke (module-level validation)
- **Logs Directory**: tests/results/logs
- **Reports Directory**: tests/results/reports

---

## Instructions to Claude

### 1. Read the Canonical Workflow

Read and execute: **planning-is-prompting → workflow/testing-remediation.md**

### 2. Apply Configuration

Use the project configuration above when executing the remediation workflow.

### 3. Remediation Scope Options

**FULL** (default):
- Fix all regressions in priority order (CRITICAL→HIGH→MEDIUM)
- Appropriate for post-development validation

**CRITICAL_ONLY**:
- Fix only blocking issues (import errors, critical functionality broken)
- Appropriate for quick fixes before commit

**SELECTIVE**:
- Present issues, user chooses which to fix
- Appropriate when unsure about impact

**ANALYSIS_ONLY**:
- Generate comparison report only, no fixes
- Appropriate for understanding what broke

### 4. Comparison Analysis

**Baseline vs Current**:
- Check if any modules that passed now fail (regressions)
- Verify smoke tests still pass after code changes
- Ensure no new import errors introduced
- Validate component functionality maintained

**Component Priority Classification**:
- **CRITICAL**: auth_checker, gemini_client (core dependencies)
- **HIGH**: pdf_processor (main functionality)
- **MEDIUM**: output_formatter, metrics (supporting components)

### 5. Expected Outcome

**If no regressions**:
- Pass rate: 100% (same as baseline)
- Regressions: 0
- Status: STABLE

**If improvements made**:
- Pass rate: ≥100% (e.g., authentication now works)
- Status: IMPROVED

**If regressions detected**:
- Pass rate: <100%
- Regressions: Listed in report with priority
- Recommended action: Fix in priority order

---

**Typical workflow**: Run /plan-test-baseline before changes, /plan-test-remediation after.
