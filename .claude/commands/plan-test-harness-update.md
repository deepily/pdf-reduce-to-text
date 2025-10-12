---
description: Analyze code changes and plan test coverage updates
allowed-tools: Bash(.*), TodoWrite, Read, Write, Edit, Grep, Glob
arguments:
  - name: date_range
    description: Date range for git log analysis (auto-detects last 7 days if not provided)
    required: false
---

# Test Harness Update for PDF Reduce to Text

**Purpose**: Identify which components were added/modified and ensure proper test coverage
**Project**: PDF Context Window Stuffing Tool
**Note**: Helps maintain smoke tests as code evolves

---

## Project Configuration

**Identity**:
- **Prefix**: [PDF-REDUCE]
- **Project Name**: PDF Context Window Stuffing Tool
- **Working Directory**: /mnt/DATA01/include/www.deepily.ai/projects/pdf-reduce-to-text

**Date Range**: ${1:-auto} (defaults to last 7 days)

**Source Directories**:
- src/
- data/ (excluded from test requirements)

**Component Classification**:
```yaml
"src/auth_checker.py":
  type: "critical"
  requires_smoke_test: true
  requires_unit_tests: false
  reason: "Core dependency for Google Cloud integration"

"src/gemini_client.py":
  type: "critical"
  requires_smoke_test: true
  requires_unit_tests: false
  reason: "Core API integration"

"src/pdf_processor.py":
  type: "critical"
  requires_smoke_test: true
  requires_unit_tests: false
  reason: "Main processing pipeline"

"src/reduce_to_text.py":
  type: "standard"
  requires_smoke_test: false
  requires_unit_tests: false
  reason: "CLI orchestrator, tested via integration"

"src/output_formatter.py":
  type: "standard"
  requires_smoke_test: true
  requires_unit_tests: false
  reason: "Output generation"

"src/metrics.py":
  type: "support"
  requires_smoke_test: true
  requires_unit_tests: false
  reason: "Analytics and reporting"
```

---

## Instructions to Claude

### 1. Read the Canonical Workflow

Read and execute: **planning-is-prompting → workflow/testing-harness-update.md**

### 2. Apply Configuration

Use the project configuration above when executing the harness update workflow.

### 3. Code Change Analysis

**For this project, "test harness updates" means**:

#### A. Changed Core Components (Critical)
**For src/auth_checker.py, src/gemini_client.py, src/pdf_processor.py**:
- ✅ Check: Has `quick_smoke_test()` function in `__main__` block?
- ✅ Check: Smoke test covers new functionality?
- ✅ Check: Module can be executed standalone: `python -m src.MODULE`?
- ✅ Check: CLAUDE.md lists module in testing commands section?

#### B. Changed Standard Components
**For src/output_formatter.py, src/metrics.py**:
- ✅ Check: Has basic smoke test or example usage?
- ✅ Check: Module imports successfully?
- ℹ️  Note: Unit tests optional for these components

#### C. New Modules Added
**For any new src/*.py file**:
- ✅ Check: Classified by criticality (critical/standard/support)?
- ✅ Check: Smoke test added if critical?
- ✅ Check: Documented in CLAUDE.md?
- ✅ Check: Import path works correctly?

### 4. Gap Analysis

**Missing Test Coverage**:
- Critical module without smoke test
- Smoke test doesn't cover new functionality
- Module can't be executed standalone
- New component not classified

**Priority Framework**:
- **CRITICAL**: Core components (auth, gemini, pdf_processor) without smoke tests
- **HIGH**: New functionality in existing modules not covered by tests
- **MEDIUM**: Standard components without basic validation
- **LOW**: Support components without examples

### 5. Expected Outcome

**Analysis report should show**:
- Changed code files: {count}
- Missing smoke tests: {count}
- Outdated smoke tests: {count}
- Priority updates: {count} critical, {count} high

**Update plan should list**:
- Which modules need new smoke tests
- Which existing tests need expansion
- Which __main__ blocks to add/update
- Template code for new smoke tests

---

**Recommended workflow**: Run after significant code changes to maintain test coverage.
