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
Output formatting module for beautiful terminal tables and file output.

Provides comprehensive formatting for:
- Rich terminal tables with compression metrics
- JSON output for programmatic access
- Markdown file generation
- Progress tracking and status updates

Requires:
    - rich library for terminal output
    - pathlib for file handling
    - json for structured output

Ensures:
    - Beautiful, readable terminal output
    - Well-formatted markdown files
    - Structured JSON data for analysis
    - Clear progress indication during processing
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text

from src.pdf_processor import ProcessingMetrics, PageContent


logger = logging.getLogger( __name__ )


class OutputFormatter:
    """
    Formatter for terminal output and file generation.

    Handles all output formatting including terminal tables,
    JSON reports, markdown files, and progress tracking.
    """

    def __init__( self, console: Optional[Console] = None ):
        """
        Initialize output formatter.

        Requires:
            - console: Rich console object (creates new if None)

        Ensures:
            - Console is available for output formatting
            - Consistent styling across all output
        """
        self.console = console or Console()


    def create_summary_table( self, results: List[Dict[str, Any]] ) -> Table:
        """
        Create a rich table summarizing processing results.

        Requires:
            - results: List of processing result dictionaries

        Ensures:
            - Returns formatted Rich table
            - Includes all key metrics and compression ratios
            - Proper alignment and styling
        """
        table = Table( show_header=True, header_style="bold blue" )

        # Add columns
        table.add_column( "File Name", style="cyan", no_wrap=True )
        table.add_column( "Original", justify="right", style="magenta" )
        table.add_column( "Text Only", justify="right", style="green" )
        table.add_column( "Text+Img+OCR", justify="right", style="green" )
        table.add_column( "Compression", justify="right", style="bold red" )
        table.add_column( "Images", justify="right", style="yellow" )
        table.add_column( "Time", justify="right", style="dim" )

        # Add rows
        for result in results:
            metrics = result["metrics"]

            # Format file sizes
            original_mb = metrics.original_size_bytes / ( 1024 * 1024 )
            text_kb = metrics.text_only_bytes / 1024
            full_kb = metrics.full_extraction_bytes / 1024

            # Format compression ratio with color coding
            compression = f"{metrics.compression_ratio:.1f}%"
            if metrics.compression_ratio > 95:
                compression_style = "bold green"
            elif metrics.compression_ratio > 90:
                compression_style = "yellow"
            else:
                compression_style = "red"

            table.add_row(
                result["filename"],
                f"{original_mb:.1f} MB",
                f"{text_kb:.0f} KB",
                f"{full_kb:.0f} KB",
                Text( compression, style=compression_style ),
                str( metrics.images_found ),
                f"{metrics.processing_time_seconds:.1f}s"
            )

        return table


    def print_processing_summary( self, results: List[Dict[str, Any]] ) -> None:
        """
        Print comprehensive processing summary to terminal.

        Requires:
            - results: List of processing result dictionaries

        Ensures:
            - Displays summary table with metrics
            - Shows overall statistics
            - Includes token usage information
        """
        if not results:
            self.console.print( "No results to display", style="yellow" )
            return

        # Create and display summary table
        summary_table = self.create_summary_table( results )
        self.console.print( summary_table )

        # Calculate totals
        total_files = len( results )
        total_original_mb = sum( r["metrics"].original_size_bytes for r in results ) / ( 1024 * 1024 )
        total_compressed_kb = sum( r["metrics"].full_extraction_bytes for r in results ) / 1024
        avg_compression = sum( r["metrics"].compression_ratio for r in results ) / total_files
        total_images = sum( r["metrics"].images_found for r in results )
        total_tokens = sum( r["metrics"].gemini_tokens_used for r in results )
        total_time = sum( r["metrics"].processing_time_seconds for r in results )

        # Display summary statistics
        self.console.print( f"\n📊 Summary Statistics:", style="bold blue" )
        self.console.print( f"   Files processed: {total_files}" )
        self.console.print( f"   Original size: {total_original_mb:.1f} MB" )
        self.console.print( f"   Compressed size: {total_compressed_kb:.0f} KB" )
        self.console.print( f"   Average compression: {avg_compression:.1f}%" )
        self.console.print( f"   Images processed: {total_images}" )
        self.console.print( f"   Gemini tokens used: {total_tokens:,}" )
        self.console.print( f"   Total processing time: {total_time:.1f}s" )


    def save_json_report( self, results: List[Dict[str, Any]], output_path: Path ) -> None:
        """
        Save processing results as JSON report.

        Requires:
            - results: List of processing result dictionaries
            - output_path: Path for JSON output file

        Ensures:
            - Creates well-formatted JSON file
            - Includes all metrics and metadata
            - Handles datetime serialization
        """
        try:
            # Prepare data for JSON serialization
            json_data = {
                "processed_at": datetime.now().isoformat(),
                "tool_version": "1.0.0",
                "files": [],
                "summary": {}
            }

            # Process each result
            for result in results:
                metrics = result["metrics"]

                file_data = {
                    "filename": result["filename"],
                    "original_size_bytes": metrics.original_size_bytes,
                    "text_only_bytes": metrics.text_only_bytes,
                    "full_extraction_bytes": metrics.full_extraction_bytes,
                    "compression_ratio": round( metrics.compression_ratio, 1 ),
                    "pages": metrics.pages_processed,
                    "images_found": metrics.images_found,
                    "processing_time_seconds": round( metrics.processing_time_seconds, 2 ),
                    "gemini_tokens_used": metrics.gemini_tokens_used
                }

                json_data["files"].append( file_data )

            # Calculate summary
            if results:
                json_data["summary"] = {
                    "total_files": len( results ),
                    "total_original_bytes": sum( r["metrics"].original_size_bytes for r in results ),
                    "total_compressed_bytes": sum( r["metrics"].full_extraction_bytes for r in results ),
                    "average_compression": round( sum( r["metrics"].compression_ratio for r in results ) / len( results ), 1 ),
                    "total_images": sum( r["metrics"].images_found for r in results ),
                    "total_gemini_tokens": sum( r["metrics"].gemini_tokens_used for r in results ),
                    "total_processing_time": round( sum( r["metrics"].processing_time_seconds for r in results ), 2 )
                }

            # Write JSON file
            with open( output_path, 'w', encoding='utf-8' ) as f:
                json.dump( json_data, f, indent=2, ensure_ascii=False )

            self.console.print( f"✅ JSON report saved: {output_path}", style="green" )

        except Exception as e:
            logger.error( f"Failed to save JSON report: {e}" )
            self.console.print( f"❌ Failed to save JSON report: {e}", style="red" )


    def save_markdown_file( self, filename: str, page_contents: List[PageContent], output_path: Path ) -> None:
        """
        Save processed content as markdown file.

        Requires:
            - filename: Original PDF filename
            - page_contents: List of PageContent objects
            - output_path: Path for markdown output file

        Ensures:
            - Creates well-formatted markdown file
            - Includes page-by-page content with structure
            - Properly formatted headers and sections
        """
        try:
            markdown_lines = []

            # Document header
            markdown_lines.append( f"# {filename} - Context Extraction" )
            markdown_lines.append( "" )
            markdown_lines.append( f"**Processed:** {datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )}" )
            markdown_lines.append( f"**Pages:** {len( page_contents )}" )
            markdown_lines.append( f"**Tool:** PDF Context Window Stuffing Experiment" )
            markdown_lines.append( "" )
            markdown_lines.append( "---" )
            markdown_lines.append( "" )

            # Add page content
            for page_content in page_contents:
                markdown_lines.append( page_content.markdown )
                markdown_lines.append( "" )

            # Write markdown file
            with open( output_path, 'w', encoding='utf-8' ) as f:
                f.write( '\n'.join( markdown_lines ) )

            self.console.print( f"✅ Markdown file saved: {output_path}", style="green" )

        except Exception as e:
            logger.error( f"Failed to save markdown file: {e}" )
            self.console.print( f"❌ Failed to save markdown file: {e}", style="red" )


    def display_processing_status( self, current_file: str, file_index: int, total_files: int ) -> None:
        """
        Display current processing status.

        Requires:
            - current_file: Name of file being processed
            - file_index: Current file index (0-based)
            - total_files: Total number of files to process

        Ensures:
            - Shows clear progress indication
            - Displays current file information
        """
        progress_text = f"[{file_index + 1}/{total_files}]"
        self.console.print( f"\n🔄 {progress_text} Processing: {current_file}", style="bold yellow" )


    def display_error( self, message: str, error: Optional[Exception] = None ) -> None:
        """
        Display error message with consistent formatting.

        Requires:
            - message: Error message to display
            - error: Optional exception object for details

        Ensures:
            - Clear error indication
            - Consistent error formatting
            - Optional detailed error information
        """
        self.console.print( f"❌ {message}", style="bold red" )
        if error:
            self.console.print( f"   Details: {error}", style="red" )


    def display_success( self, message: str ) -> None:
        """
        Display success message with consistent formatting.

        Requires:
            - message: Success message to display

        Ensures:
            - Clear success indication
            - Consistent success formatting
        """
        self.console.print( f"✅ {message}", style="bold green" )


    def create_progress_bar( self, description: str ) -> Progress:
        """
        Create a Rich progress bar for long operations.

        Requires:
            - description: Description for the progress bar

        Ensures:
            - Returns configured Rich Progress object
            - Includes spinner, text, bar, and percentage
        """
        return Progress(
            SpinnerColumn(),
            TextColumn( "[progress.description]{task.description}" ),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )


if __name__ == "__main__":
    """Test the output formatter when run directly."""
    import random

    # Create test data
    test_results = []
    for i in range( 3 ):
        test_results.append( {
            "filename": f"test_document_{i + 1}.pdf",
            "metrics": ProcessingMetrics(
                original_size_bytes=random.randint( 1000000, 20000000 ),
                text_only_bytes=random.randint( 50000, 200000 ),
                full_extraction_bytes=random.randint( 100000, 300000 ),
                compression_ratio=random.uniform( 90, 99 ),
                pages_processed=random.randint( 10, 100 ),
                images_found=random.randint( 5, 50 ),
                processing_time_seconds=random.uniform( 10, 60 ),
                gemini_tokens_used=random.randint( 5000, 25000 )
            )
        } )

    # Test formatter
    formatter = OutputFormatter()
    formatter.print_processing_summary( test_results )

    print( f"\n✅ Output formatter test completed" )