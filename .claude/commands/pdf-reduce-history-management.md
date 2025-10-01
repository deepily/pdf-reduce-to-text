Execute the canonical history management workflow from planning-is-prompting → workflow/history-management.md

Use the following project-specific configuration:

**Project**: PDF Context Window Stuffing Tool
**Prefix**: `[PDF-REDUCE]`
**History Location**: `/mnt/DATA01/include/www.deepily.ai/projects/pdf-reduce-to-text/history.md`
**Archive Location**: `/mnt/DATA01/include/www.deepily.ai/projects/pdf-reduce-to-text/history/`

**Token Thresholds** (defaults):
- Warning: 20,000 tokens
- Critical: 22,000 tokens
- Hard limit: 25,000 tokens

**Retention Targets** (defaults):
- Target tokens: 8-12k tokens
- Target days: 7-14 days recent history

**Operational Mode**: {mode}

Supported modes:
- `mode=check` (default) - Health check with velocity forecasting
- `mode=archive` - Execute adaptive archival split
- `mode=analyze` - Deep trend analysis with recommendations
- `mode=dry-run` - Simulate archive without making changes

If no mode is specified, default to mode=check.
