#!/usr/bin/env python3

# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
PDF Context Window Stuffing Tool - Main CLI Entry Point

This tool extracts text from PDFs and uses Gemini 2.5 Flash to generate
image descriptions and OCR, creating a compressed text representation
suitable for context window stuffing in Gemini Live.

Automatically validates Google Cloud credentials before any operations.

Usage:
    python reduce_to_text.py process --verbose
    python reduce_to_text.py process --file document.pdf
    python reduce_to_text.py report
    python reduce_to_text.py clean

Features:
    - Automatic GCP credential validation on every command
    - Latest Gemini 2.5 Flash model integration
    - Page-by-page text extraction with PyMuPDF
    - Image description and OCR via Gemini
    - Comprehensive compression metrics
    - Rich terminal output with progress tracking
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint


# Import our modules
from src.auth_checker import validate_credentials_or_exit, get_gcp_location

# Global console for rich output
console = Console()

# Project-wide configuration
PROJECT_CONFIG = {
    "model": "gemini-2.5-flash",  # Latest Gemini 2.5 Flash model
    "temperature": 0.2,           # Low for consistent extraction
    "max_output_tokens": 2048,    # Increased for detailed descriptions
    "image_max_dimension": 1024,  # Resize large images
    "batch_size": 5,              # Files to process in parallel
}


@click.group( invoke_without_command=True )
@click.option( "--skip-api-test", is_flag=True, help="Skip API connection test (for offline testing)" )
@click.pass_context
def cli( ctx, skip_api_test: bool ):
    """
    PDF Context Window Stuffing Tool

    Extracts text from PDFs and uses Gemini 2.5 Flash to create compressed
    text representations with image descriptions and OCR for context window optimization.

    🔐 Automatically validates Google Cloud credentials and tests API connection before any operation.
    """
    # ALWAYS validate credentials on ANY command - no manual step needed!
    # Test API connection unless explicitly skipped
    test_api = not skip_api_test
    project_id = validate_credentials_or_exit( test_api=test_api )
    location = get_gcp_location()

    # Store in context for subcommands
    ctx.ensure_object( dict )
    ctx.obj["project_id"] = project_id
    ctx.obj["location"] = location

    # If no subcommand provided, show help
    if ctx.invoked_subcommand is None:
        click.echo( ctx.get_help() )


@cli.command()
@click.option( "--verbose", "-v", is_flag=True, help="Enable verbose output" )
@click.option( "--debug", is_flag=True, help="Enable debug mode with detailed logging" )
@click.option( "--file", "-f", help="Process specific PDF file instead of all files in input/" )
@click.option( "--model", "-m", default=PROJECT_CONFIG["model"], help="Gemini model to use" )
@click.option( "--output-dir", "-o", default="data/output", help="Output directory for results" )
@click.option( "--page-limit", type=int, help="Process only first N pages (for testing)" )
@click.option( "--test-extraction-only", is_flag=True, help="Test PDF extraction without Gemini processing" )
@click.option( "--dry-run", is_flag=True, help="Show what would be processed without actually doing it" )
@click.pass_context
def process( ctx, verbose: bool, debug: bool, file: Optional[str], model: str, output_dir: str, page_limit: Optional[int], test_extraction_only: bool, dry_run: bool ):
    """
    Process PDFs and extract text with image descriptions and OCR.

    Automatically validates credentials and uses Gemini 2.5 Flash for image processing.
    Creates markdown output files and compression metrics.
    """
    # Credentials already validated by cli()
    project_id = ctx.obj["project_id"]
    location = ctx.obj["location"]

    # Set debug mode
    if debug:
        import logging
        logging.basicConfig( level=logging.DEBUG )
        console.print( "🐛 Debug mode enabled", style="yellow" )

    # Show processing mode
    mode_flags = []
    if test_extraction_only:
        mode_flags.append( "extraction-only" )
    if dry_run:
        mode_flags.append( "dry-run" )
    if page_limit:
        mode_flags.append( f"page-limit={page_limit}" )

    mode_str = f" ({', '.join(mode_flags)})" if mode_flags else ""

    console.print( f"\n🚀 Starting PDF processing{mode_str} with {model}", style="bold green" )
    console.print( f"📍 Project: {project_id} | Location: {location}" )

    if verbose or debug:
        console.print( f"🔧 Configuration: {PROJECT_CONFIG}" )

    # Determine input files
    if file:
        input_files = [ Path( file ) ]
        if not input_files[0].exists():
            console.print( f"❌ File not found: {file}", style="bold red" )
            sys.exit( 1 )
    else:
        input_dir = Path( "data/input" )
        if not input_dir.exists():
            console.print( f"❌ Input directory not found: {input_dir}", style="bold red" )
            console.print( "Create the directory and add PDF files to process" )
            sys.exit( 1 )

        input_files = list( input_dir.glob( "*.pdf" ) )
        if not input_files:
            console.print( f"❌ No PDF files found in {input_dir}", style="bold red" )
            sys.exit( 1 )

    console.print( f"\n📁 Found {len( input_files )} PDF file(s) to process:" )
    for pdf_file in input_files:
        size_mb = pdf_file.stat().st_size / ( 1024 * 1024 )
        console.print( f"   • {pdf_file.name} ({size_mb:.1f} MB)" )

    # Ensure output directory exists
    output_path = Path( output_dir )
    if not dry_run:
        output_path.mkdir( parents=True, exist_ok=True )

    # Handle dry run
    if dry_run:
        console.print( f"\n🎯 DRY RUN - Would process {len( input_files )} file(s):", style="bold cyan" )
        for pdf_file in input_files:
            size_mb = pdf_file.stat().st_size / ( 1024 * 1024 )
            console.print( f"   • {pdf_file.name} ({size_mb:.1f} MB)" )
            if page_limit:
                console.print( f"     → Limited to first {page_limit} pages" )
            if test_extraction_only:
                console.print( f"     → Would extract text/images only (no Gemini)" )
            else:
                console.print( f"     → Would process images with {model}" )
        console.print( f"\n✅ Dry run complete - no files were actually processed", style="green" )
        return

    # Import processing modules
    try:
        from src.gemini_client import GeminiImageProcessor
        from src.pdf_processor import PDFProcessor
        from src.output_formatter import OutputFormatter
        from src.metrics import MetricsAnalyzer
    except ImportError as e:
        console.print( f"❌ Import error: {e}", style="bold red" )
        if debug:
            import traceback
            console.print( traceback.format_exc() )
        sys.exit( 1 )

    # Initialize processors
    try:
        if test_extraction_only:
            console.print( f"\n🔧 Testing PDF extraction only (no Gemini processing)", style="yellow" )
            gemini_processor = None
        else:
            gemini_processor = GeminiImageProcessor(
                project_id=project_id,
                location=location,
                model_name=model,
                debug=debug,
                verbose=verbose
            )

        pdf_processor = PDFProcessor(
            gemini_processor=gemini_processor,
            debug=debug,
            verbose=verbose
        )

        formatter = OutputFormatter( console )
        analyzer = MetricsAnalyzer( debug=debug )

        console.print( f"✅ Processors initialized successfully", style="green" )

    except Exception as e:
        console.print( f"❌ Failed to initialize processors: {e}", style="bold red" )
        if debug:
            import traceback
            console.print( traceback.format_exc() )
        sys.exit( 1 )

    # Process each file
    results = []
    for i, pdf_file in enumerate( input_files ):
        formatter.display_processing_status( pdf_file.name, i, len( input_files ) )

        # In dot mode, show file counter
        if not verbose and not debug:
            print( f"[{i + 1}/{len( input_files )}] ", end="", flush=True )

        try:
            if test_extraction_only:
                # Test extraction without Gemini processing
                console.print( f"📖 Extracting text and images from {pdf_file.name}..." )

                # Simple test - just try to open PDF and extract first page
                import fitz
                doc = fitz.open( pdf_file )
                console.print( f"   ✅ PDF opened successfully: {len( doc )} pages" )

                if page_limit:
                    pages_to_process = min( page_limit, len( doc ) )
                else:
                    pages_to_process = len( doc )

                console.print( f"   📄 Would process {pages_to_process} pages" )

                # Test first page text extraction
                if len( doc ) > 0:
                    page = doc[0]
                    text = page.get_text( "text" )
                    images = page.get_images( full=True )
                    console.print( f"   📝 Page 1: {len( text )} chars text, {len( images )} images" )

                doc.close()
                console.print( f"   ✅ Extraction test complete for {pdf_file.name}" )

            else:
                # Full processing with Gemini
                console.print( f"🤖 Processing with Gemini 2.5 Flash..." )
                page_contents, metrics = pdf_processor.process_pdf( pdf_file )

                # Limit pages if specified
                if page_limit and len( page_contents ) > page_limit:
                    console.print( f"   🔄 Limiting to first {page_limit} pages" )
                    page_contents = page_contents[:page_limit]

                # Save outputs
                markdown_dir = output_path / "markdown"
                markdown_dir.mkdir( exist_ok=True )

                formatter.save_markdown_file(
                    pdf_file.name,
                    page_contents,
                    markdown_dir / f"{pdf_file.stem}.md"
                )

                results.append( {
                    "filename": pdf_file.name,
                    "metrics": metrics
                } )

                # Print newline if dots were printed during processing
                if not verbose and not debug and (pdf_processor.dots_printed or (gemini_processor and gemini_processor.dots_printed)):
                    print()  # Close dot line

                console.print( f"   ✅ Processed {metrics.pages_processed} pages, {metrics.images_found} images" )

        except Exception as e:
            formatter.display_error( f"Failed to process {pdf_file.name}", e )
            if debug:
                import traceback
                console.print( traceback.format_exc() )
            continue

    # Generate summary for full processing
    if not test_extraction_only and results:
        console.print( f"\n📊 Processing Summary:", style="bold blue" )
        formatter.print_processing_summary( results )

        # Save JSON report
        json_path = output_path / "metrics.json"
        formatter.save_json_report( results, json_path )

        # Save analysis report
        analysis_path = output_path / "analysis.json"
        analyzer.save_analysis_report( results, analysis_path )

    console.print( f"\n✅ Processing complete!", style="bold green" )


@cli.command()
@click.option( "--output-dir", "-o", default="data/output", help="Output directory to check" )
def report( output_dir: str ):
    """
    Generate summary report of processed files and compression metrics.
    """
    console.print( f"\n📊 Generating compression report from {output_dir}", style="bold blue" )

    output_path = Path( output_dir )
    if not output_path.exists():
        console.print( f"❌ Output directory not found: {output_dir}", style="bold red" )
        sys.exit( 1 )

    # Discover metrics files from all processing runs
    metrics_files = list( output_path.glob( "metrics-*.json" ) )
    if not metrics_files:
        # Also check for legacy metrics.json files
        legacy_files = list( output_path.glob( "metrics.json" ) )
        if legacy_files:
            metrics_files = legacy_files
        else:
            console.print( f"❌ No metrics files found in {output_dir}", style="bold red" )
            console.print( f"   Run 'python src/reduce_to_text.py process' first to generate data" )
            sys.exit( 1 )

    console.print( f"📄 Found {len( metrics_files )} processing run(s):" )

    # Load and aggregate all metrics data directly from JSON
    all_files_data = []
    run_details = []

    # Aggregated totals
    total_files_processed = 0
    total_original_bytes = 0
    total_compressed_bytes = 0
    total_processing_time = 0
    total_pages = 0
    total_images = 0
    total_tokens = 0

    for metrics_file in sorted( metrics_files ):
        try:
            with open( metrics_file, 'r' ) as f:
                metrics_data = json.load( f )

            # Extract run details for display
            processed_at = metrics_data.get( "processed_at", "Unknown" )
            file_count = len( metrics_data.get( "files", [] ) )

            # Aggregate file data
            for file_data in metrics_data.get( "files", [] ):
                all_files_data.append( file_data )
                total_files_processed += 1
                total_original_bytes += file_data.get( "original_size_bytes", 0 )
                total_compressed_bytes += file_data.get( "full_extraction_bytes", 0 )
                total_processing_time += file_data.get( "processing_time_seconds", 0 )
                total_pages += file_data.get( "pages", 0 )
                total_images += file_data.get( "images_found", 0 )
                total_tokens += file_data.get( "gemini_tokens_used", 0 )

            run_details.append( {
                "file": metrics_file.name,
                "timestamp": processed_at,
                "files": file_count
            } )

        except Exception as e:
            console.print( f"⚠️  Failed to load {metrics_file.name}: {e}", style="yellow" )
            continue

    if not all_files_data:
        console.print( f"❌ No valid metrics data found", style="bold red" )
        sys.exit( 1 )

    # Display run summary
    for run in run_details:
        timestamp_str = run["timestamp"][:19] if len( run["timestamp"] ) > 19 else run["timestamp"]
        console.print( f"   • {run['file']}: {run['files']} file(s) at {timestamp_str}" )

    console.print( f"\n📈 Aggregate Analysis across {total_files_processed} file(s):", style="bold green" )

    # Display file-by-file table
    table = Table( title="PDF Processing Summary" )
    table.add_column( "File Name", style="cyan", no_wrap=True )
    table.add_column( "Original (MB)", justify="right" )
    table.add_column( "Compressed (KB)", justify="right" )
    table.add_column( "Compression", justify="right" )
    table.add_column( "Pages", justify="right" )
    table.add_column( "Images", justify="right" )
    table.add_column( "Time (min)", justify="right" )

    for file_data in all_files_data:
        original_mb = file_data.get( "original_size_bytes", 0 ) / ( 1024 * 1024 )
        compressed_kb = file_data.get( "full_extraction_bytes", 0 ) / 1024
        compression = file_data.get( "compression_ratio", 0 )
        pages = file_data.get( "pages", 0 )
        images = file_data.get( "images_found", 0 )
        time_min = file_data.get( "processing_time_seconds", 0 ) / 60

        table.add_row(
            file_data.get( "filename", "Unknown" ),
            f"{original_mb:.1f}",
            f"{compressed_kb:.0f}",
            f"{compression:.1f}%",
            str( pages ),
            str( images ),
            f"{time_min:.1f}"
        )

    console.print( table )

    # Calculate aggregated metrics
    if total_original_bytes > 0:
        overall_compression = ( 1 - total_compressed_bytes / total_original_bytes ) * 100
    else:
        overall_compression = 0

    space_saved_mb = ( total_original_bytes - total_compressed_bytes ) / ( 1024 * 1024 )

    # Cost calculation (assuming $0.075 per 1M tokens for Gemini 2.5 Flash)
    cost_per_million_tokens = 0.075
    estimated_cost = ( total_tokens / 1_000_000 ) * cost_per_million_tokens

    # Performance calculations
    avg_processing_time = total_processing_time / total_files_processed if total_files_processed > 0 else 0
    files_per_minute = 60 / avg_processing_time if avg_processing_time > 0 else 0
    pages_per_minute = ( total_pages * 60 ) / total_processing_time if total_processing_time > 0 else 0
    images_per_minute = ( total_images * 60 ) / total_processing_time if total_processing_time > 0 else 0

    console.print( f"\n💰 Cost Analysis:", style="bold cyan" )
    console.print( f"   Total tokens used: {total_tokens:,}" )
    console.print( f"   Estimated total cost: ${estimated_cost:.4f}" )
    console.print( f"   Average cost per file: ${estimated_cost/total_files_processed:.4f}" )

    console.print( f"\n⚡ Performance Analysis:", style="bold cyan" )
    console.print( f"   Total processing time: {total_processing_time/60:.1f} minutes" )
    console.print( f"   Average processing time: {avg_processing_time:.1f} seconds" )
    console.print( f"   Processing rate: {files_per_minute:.2f} files/minute" )
    console.print( f"   Page processing rate: {pages_per_minute:.1f} pages/minute" )
    console.print( f"   Image processing rate: {images_per_minute:.1f} images/minute" )

    console.print( f"\n🗜️  Compression Analysis:", style="bold cyan" )
    console.print( f"   Overall compression ratio: {overall_compression:.1f}%" )
    console.print( f"   Total space saved: {space_saved_mb:.1f} MB" )
    console.print( f"   Original total size: {total_original_bytes/(1024*1024):.1f} MB" )
    console.print( f"   Compressed total size: {total_compressed_bytes/1024:.0f} KB" )

    # Generate recommendations
    recommendations = []
    if estimated_cost / total_files_processed > 0.10:
        recommendations.append( "Consider batch processing to reduce per-file overhead" )
    if images_per_minute < 10:
        recommendations.append( "Image processing is slow - consider resizing images before processing" )
    if overall_compression < 90:
        recommendations.append( "Low compression ratio - PDFs may have mostly text content" )
    if total_processing_time > 3600:  # More than 1 hour total
        recommendations.append( "Consider parallel processing for large batches" )

    if not recommendations:
        recommendations.append( "Processing appears optimized - no immediate improvements needed" )

    console.print( f"\n💡 Recommendations:", style="bold yellow" )
    for rec in recommendations:
        console.print( f"   • {rec}" )


@cli.command()
@click.option( "--output-dir", "-o", default="data/output", help="Output directory to clean" )
@click.confirmation_option( prompt="Are you sure you want to delete all output files?" )
def clean( output_dir: str ):
    """
    Clean output directory (removes all processed files).
    """
    console.print( f"\n🧹 Cleaning output directory: {output_dir}", style="bold yellow" )

    output_path = Path( output_dir )
    if not output_path.exists():
        console.print( f"❌ Output directory not found: {output_dir}", style="bold red" )
        return

    # Remove all files in output directory
    deleted_count = 0
    for file_path in output_path.rglob( "*" ):
        if file_path.is_file():
            file_path.unlink()
            deleted_count += 1

    console.print( f"✅ Deleted {deleted_count} files from {output_dir}", style="bold green" )


@cli.command()
@click.pass_context
def status( ctx ):
    """
    Show current authentication status and configuration.
    """
    # Credentials already validated by cli()
    project_id = ctx.obj["project_id"]
    location = ctx.obj["location"]

    console.print( f"\n✅ Authentication Status", style="bold green" )

    # Create status table
    table = Table( show_header=True, header_style="bold blue" )
    table.add_column( "Setting" )
    table.add_column( "Value" )

    table.add_row( "Project ID", project_id )
    table.add_row( "Location", location )
    table.add_row( "Gemini Model", PROJECT_CONFIG["model"] )
    table.add_row( "Temperature", str( PROJECT_CONFIG["temperature"] ) )
    table.add_row( "Max Tokens", str( PROJECT_CONFIG["max_output_tokens"] ) )

    console.print( table )

    # Check directory structure
    console.print( f"\n📁 Directory Structure:", style="bold blue" )

    dirs_to_check = [
        ( "data/input", "Input PDF files" ),
        ( "data/output", "Processed results" ),
        ( "src/", "Source code" ),
    ]

    for dir_path, description in dirs_to_check:
        path = Path( dir_path )
        if path.exists():
            if path.is_dir():
                file_count = len( list( path.iterdir() ) )
                console.print( f"   ✅ {dir_path} - {description} ({file_count} items)" )
            else:
                console.print( f"   ⚠️  {dir_path} - Exists but not a directory" )
        else:
            console.print( f"   ❌ {dir_path} - Not found" )


if __name__ == "__main__":
    """Entry point when run directly."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print( f"\n\n⚠️  Operation cancelled by user", style="yellow" )
        sys.exit( 130 )  # Standard exit code for Ctrl+C
    except Exception as e:
        console.print( f"\n❌ Unexpected error: {e}", style="bold red" )
        if "--verbose" in sys.argv or "-v" in sys.argv:
            import traceback
            console.print( traceback.format_exc() )
        sys.exit( 1 )