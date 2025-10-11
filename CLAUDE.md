# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

**Short Project Prefix**: `[PDF-REDUCE]`

Use this prefix in all todo lists, notifications, and queries requiring user approval or guidance.

## Project Overview

PDF Context Window Stuffing Tool - A CLI experiment that extracts text from PDFs and uses Gemini 2.5 Flash to generate image descriptions and OCR, creating compressed text representations suitable for context window optimization in Gemini Live.

## Key Commands

### Development Commands
- `python reduce_to_text.py process` - Process PDFs in data/input/ directory
- `python reduce_to_text.py process --verbose` - Process with detailed progress output
- `python reduce_to_text.py process --debug` - Process with debug logging
- `python reduce_to_text.py process --file document.pdf` - Process specific PDF file
- `python reduce_to_text.py process --dry-run` - Preview processing without executing
- `python reduce_to_text.py process --test-extraction-only` - Test PDF extraction without Gemini API calls

### Alternative Entry Points
- `python -m src process` - Run via module entry point
- `python src/reduce_to_text.py process` - Direct script execution

### Utility Commands
- `python reduce_to_text.py report` - Generate compression and cost analysis report
- `python reduce_to_text.py status` - Check authentication and configuration status
- `python reduce_to_text.py clean` - Clean output directory (with confirmation)

### Testing Commands
- `python src/auth_checker.py` - Test Google Cloud authentication
- `python src/gemini_client.py` - Test Gemini 2.5 Flash client
- `python src/pdf_processor.py` - Test PDF processing components
- `pytest` - Run test suite (if tests exist)

### Environment Setup
- Requires Google Cloud credentials: `gcloud auth application-default login`
- Requires PROJECT_ID environment variable or project from credentials
- Requires input PDFs in `data/input/` directory
- Output generated in `data/output/` directory

## Architecture

### Core Components

**Authentication Pipeline**: Automatic GCP credential validation on every command - no manual auth steps required. Built into CLI entry point.

**Processing Pipeline**: PDF → Text Extraction → Image Extraction → Gemini AI Analysis → Markdown Generation → Metrics Calculation

**Data Flow Architecture**:
1. `auth_checker.py` - Validates Google Cloud credentials and API connectivity
2. `pdf_processor.py` - Extracts text and images from PDF pages using PyMuPDF
3. `gemini_client.py` - Processes images with Gemini 2.5 Flash for descriptions and OCR
4. `output_formatter.py` - Generates markdown files and terminal tables with Rich
5. `metrics.py` - Calculates compression ratios and performance analytics
6. `reduce_to_text.py` - CLI orchestrator using Click framework

### Key Design Patterns

**Unified Output System**: All components use consistent `_output()` method supporting:
- Minimal mode: Dot progress indicators with file counters
- Verbose mode: Stage-by-stage progress with emoji indicators
- Debug mode: Technical logging with throttled output
- Hybrid modes for combined visibility

**Gemini 2.5 Flash Integration**: Latest model with thinking capabilities for optimal image processing. Dual-mode operation for both image descriptions and OCR text extraction.

**Modular Architecture**: Each component is independently testable with Design by Contract docstrings. Clear separation of concerns between PDF processing, AI analysis, and output formatting.

## Directory Structure

```
data/
├── input/          # Place PDF files here for processing
└── output/         # Generated outputs
    ├── markdown/   # Compressed text representations
    ├── metrics-*.json  # Processing metrics per run
    └── analysis-*.json # Detailed analysis reports

src/                # Core implementation modules
rnd/               # Research and design documents
└── 2025.09.23-context-stuffing-design.md  # Architecture design doc
```

## Critical Configuration

**Model Configuration**: Uses `gemini-2.5-flash` model with optimized prompts for context window stuffing:
- Image descriptions focus on text content, visual elements, and document structure
- OCR extraction preserves formatting and handles complex layouts
- Image preprocessing (1024px max dimension) to optimize token usage

**Rate Limiting**: Built-in 100ms delays between Gemini API calls to respect quotas and avoid throttling.

**Error Handling**: Graceful failures with detailed remediation instructions. Supports offline testing with `--skip-api-test` flag.

## Development Guidelines

### Authentication Requirements
- Every CLI command automatically validates Google Cloud credentials
- No manual auth steps required - built into CLI entry point
- Clear error messages with step-by-step remediation instructions
- API connectivity testing before processing begins

### Output Patterns
- Use `_output()` method for consistent verbosity levels across components
- Track `dots_printed` flag for proper newline management in minimal mode
- Prefer emoji indicators in verbose mode for clear progress visibility
- Throttle debug output to avoid overwhelming console in debug mode

### Processing Patterns
- Process PDFs page-by-page to minimize memory usage
- Extract images to temp directory with structured naming (page_N_img_M.ext)
- Clean up temporary files after processing
- Generate both text-only and full extraction metrics for comparison

### Error Recovery
- Handle PDF corruption gracefully with clear error messages
- Retry logic for transient API failures
- Continue processing remaining files if individual files fail
- Preserve partial results and report processing status

## Testing Approach

**Component Testing**: Each module includes standalone testing when run directly:
```bash
python src/auth_checker.py      # Test authentication flow
python src/gemini_client.py     # Test Gemini API client
python src/pdf_processor.py     # Test PDF processing
```

**Integration Testing**: Use `--dry-run` and `--test-extraction-only` flags for safe testing without API costs.

**Validation Strategy**: Manual review of markdown outputs for quality assessment. Compression ratio targets of 90%+ for image-heavy documents.

## Cost Management

**Token Optimization**:
- Resize large images to 1024px max dimension
- Use optimized prompts to minimize token usage
- Track token consumption per file and provide cost estimates
- Current pricing assumes $0.075 per 1M tokens for Gemini 2.5 Flash

**Batch Processing**: Process multiple files efficiently with progress tracking and error recovery to minimize per-file overhead costs.

## Implementation History

Read `rnd/2025.09.23-context-stuffing-design.md` for complete technical architecture, research questions, and validation plan. Key phases completed include core infrastructure, image processing, metrics analysis, and comprehensive verbosity system.

## Installed Workflows

**Session Management**:
- `/plan-session-start` - Initialize work session (load history, identify TODOs, present context)
- `/plan-session-end` - Wrap up session (update history, commit changes, send notifications)

**History Management**:
- `/plan-history-management` - Manage history.md archival (modes: check/archive/analyze/dry-run)

**Backup Infrastructure**:
- `/plan-backup` - Dry-run backup preview (safe default)
- `/plan-backup --write` - Execute actual backup
- `/plan-backup --check-for-update` - Check for script updates

**Configuration**:
- History file: ./history.md
- Archive directory: ./history/
- Planning documents: ./rnd/
- Backup source: /mnt/DATA01/include/www.deepily.ai/projects/pdf-reduce-to-text/
- Backup destination: /mnt/DATA02/include/www.deepily.ai/projects/pdf-reduce-to-text/
- Backup exclusions: src/scripts/conf/rsync-exclude.txt

## Session Workflows

**Session Start**: Use `/plan-session-start` or see planning-is-prompting → workflow/session-start.md

**Session End**: Use `/plan-session-end` or see planning-is-prompting → workflow/session-end.md

**History Management**: See planning-is-prompting → workflow/history-management.md

**Backup Management**: See planning-is-prompting → workflow/backup-version-check.md