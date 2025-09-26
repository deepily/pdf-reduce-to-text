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
PDF processing module using PyMuPDF for text and image extraction.

Provides comprehensive PDF analysis including:
- Page-by-page text extraction
- Image extraction with position metadata
- Integration with Gemini 2.5 Flash for image processing
- Markdown output generation
- Compression metrics calculation

Requires:
    - PyMuPDF (fitz) for PDF processing
    - Pillow for image handling
    - Gemini client for image descriptions and OCR

Ensures:
    - High-quality text extraction preserving structure
    - Complete image extraction with metadata
    - Formatted markdown output for each page
    - Accurate compression ratio calculations
"""

import fitz  # PyMuPDF
import io
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from PIL import Image

from src.gemini_client import GeminiImageProcessor


logger = logging.getLogger( __name__ )


@dataclass
class ImageInfo:
    """
    Information about an extracted image.

    Attributes:
        page_number: PDF page number (0-indexed)
        image_index: Image index on the page
        position: (x, y) position on page
        size: (width, height) in pixels
        file_path: Path to extracted image file
        description: Gemini-generated description
        ocr_text: Gemini-extracted text
    """
    page_number: int
    image_index: int
    position: Tuple[float, float]
    size: Tuple[int, int]
    file_path: Path
    description: str = ""
    ocr_text: str = ""


@dataclass
class PageContent:
    """
    Content extracted from a PDF page.

    Attributes:
        page_number: PDF page number (0-indexed)
        text: Plain text content
        images: List of images on this page
        markdown: Formatted markdown representation
    """
    page_number: int
    text: str
    images: List[ImageInfo]
    markdown: str = ""


@dataclass
class ProcessingMetrics:
    """
    Metrics for PDF processing and compression analysis.

    Attributes:
        original_size_bytes: Original PDF file size
        text_only_bytes: Size of extracted text only
        full_extraction_bytes: Size including descriptions and OCR
        compression_ratio: Percentage compression achieved
        pages_processed: Number of pages processed
        images_found: Total images extracted
        processing_time_seconds: Total processing time
        gemini_tokens_used: Total Gemini API tokens consumed
    """
    original_size_bytes: int
    text_only_bytes: int
    full_extraction_bytes: int
    compression_ratio: float
    pages_processed: int
    images_found: int
    processing_time_seconds: float
    gemini_tokens_used: int


class PDFProcessor:
    """
    PDF processor with text extraction and Gemini image analysis.

    Handles complete PDF processing including text extraction,
    image extraction, Gemini-powered image descriptions and OCR,
    and markdown output generation.
    """

    def __init__(
        self,
        gemini_processor: GeminiImageProcessor,
        debug: bool = False,
        verbose: bool = False,
        temp_dir: Optional[Path] = None
    ):
        """
        Initialize PDF processor.

        Requires:
            - gemini_processor: Initialized Gemini client for image processing
            - debug: Enable debug logging
            - verbose: Enable verbose progress output
            - temp_dir: Directory for temporary image files (uses system temp if None)

        Ensures:
            - Processor is ready for PDF analysis
            - Temporary directory is available for image extraction
            - Gemini client is properly configured
        """
        self.gemini_processor = gemini_processor
        self.debug = debug
        self.verbose = verbose
        self.temp_dir = Path( temp_dir ) if temp_dir else Path( tempfile.gettempdir() )

        # Output tracking for dot mode
        self.dots_printed = False

        if debug:
            logger.setLevel( logging.DEBUG )
            logger.debug( f"PDF processor initialized with temp dir: {self.temp_dir}" )

        # Ensure temp directory exists
        self.temp_dir.mkdir( parents=True, exist_ok=True )


    def _output( self, message: str, level: str = "verbose" ):
        """
        Unified output handler for different verbosity levels.

        Requires:
            - message: Message to output
            - level: Output level ("dot", "verbose", "debug")

        Ensures:
            - Appropriate output based on debug/verbose flags
            - Tracks dot printing for newline management
        """
        if level == "dot" and not self.verbose and not self.debug:
            print( ".", end="", flush=True )
            self.dots_printed = True
        elif level == "verbose" and self.verbose:
            print( message, flush=True )
        elif level == "debug" and self.debug and not self.verbose:
            # Throttled debug output for key checkpoints only
            print( f"[DEBUG] {message}" )
        elif level == "debug" and self.debug and self.verbose:
            # Full debug output when both flags are enabled
            print( f"[DEBUG] {message}", flush=True )


    def _extract_page_text( self, page: fitz.Page ) -> str:
        """
        Extract text from a PDF page preserving structure.

        Requires:
            - page: PyMuPDF page object

        Ensures:
            - Returns clean text with preserved formatting
            - Handles various text layouts and orientations
            - Removes excessive whitespace while preserving structure
        """
        try:
            # Get text with layout preservation
            text = page.get_text( "text" )

            # Clean up the text while preserving structure
            lines = text.split( '\n' )
            cleaned_lines = []

            for line in lines:
                # Remove excessive whitespace but preserve indentation
                cleaned_line = ' '.join( line.split() )
                if cleaned_line.strip():  # Only add non-empty lines
                    cleaned_lines.append( cleaned_line )

            return '\n'.join( cleaned_lines )

        except Exception as e:
            logger.error( f"Failed to extract text from page: {e}" )
            return ""


    def _extract_page_images( self, page: fitz.Page, page_number: int ) -> List[ImageInfo]:
        """
        Extract all images from a PDF page.

        Requires:
            - page: PyMuPDF page object
            - page_number: Page number (0-indexed)

        Ensures:
            - Returns list of ImageInfo objects with metadata
            - Extracts images to temporary files
            - Captures position and size information
            - Handles various image formats

        Raises:
            - Exception: If image extraction fails
        """
        images = []

        try:
            # Get image list from page
            image_list = page.get_images( full=True )

            if self.debug:
                logger.debug( f"Found {len( image_list )} images on page {page_number + 1}" )

            for img_index, img in enumerate( image_list ):
                try:
                    # Extract image data
                    xref = img[0]
                    base_image = page.parent.extract_image( xref )
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Get image position and size on page
                    image_rects = page.get_image_rects( xref )
                    if image_rects:
                        rect = image_rects[0]  # Use first occurrence
                        position = ( rect.x0, rect.y0 )
                        display_size = ( int( rect.width ), int( rect.height ) )
                    else:
                        position = ( 0, 0 )
                        display_size = ( 0, 0 )

                    # Save image to temporary file
                    image_filename = f"page_{page_number + 1}_img_{img_index + 1}.{image_ext}"
                    image_path = self.temp_dir / image_filename

                    with open( image_path, "wb" ) as img_file:
                        img_file.write( image_bytes )

                    # Get actual image dimensions
                    with Image.open( image_path ) as pil_img:
                        actual_size = pil_img.size

                    # Create ImageInfo object
                    image_info = ImageInfo(
                        page_number=page_number,
                        image_index=img_index,
                        position=position,
                        size=actual_size,
                        file_path=image_path
                    )

                    images.append( image_info )

                    if self.debug:
                        logger.debug( f"Extracted image {img_index + 1}: {actual_size} pixels at {position}" )

                except Exception as e:
                    logger.warning( f"Failed to extract image {img_index} from page {page_number + 1}: {e}" )
                    continue

            return images

        except Exception as e:
            logger.error( f"Failed to extract images from page {page_number + 1}: {e}" )
            return []


    def _process_images_with_gemini( self, images: List[ImageInfo] ) -> None:
        """
        Process images with Gemini for descriptions and OCR.

        Requires:
            - images: List of ImageInfo objects with valid file paths

        Ensures:
            - Updates ImageInfo objects with descriptions and OCR text
            - Handles API errors gracefully
            - Tracks token usage
        """
        for image_info in images:
            try:
                if self.debug:
                    logger.debug( f"Processing image with Gemini: {image_info.file_path.name}" )

                # Generate description
                description = self.gemini_processor.generate_image_description( image_info.file_path )
                image_info.description = description

                # Extract text via OCR
                ocr_text = self.gemini_processor.extract_text_from_image( image_info.file_path )
                image_info.ocr_text = ocr_text

                if self.debug:
                    logger.debug( f"Generated description: {description[:100]}..." )
                    if ocr_text.strip():
                        logger.debug( f"Extracted OCR text: {ocr_text[:100]}..." )

            except Exception as e:
                logger.warning( f"Failed to process image {image_info.file_path} with Gemini: {e}" )
                image_info.description = f"[Error generating description: {e}]"
                image_info.ocr_text = ""


    def _generate_page_markdown( self, page_content: PageContent ) -> str:
        """
        Generate markdown representation of page content.

        Requires:
            - page_content: PageContent object with text and images

        Ensures:
            - Returns well-formatted markdown
            - Includes page text, image descriptions, and OCR
            - Uses clear section headers and formatting
        """
        markdown_lines = []

        # Page header
        markdown_lines.append( f"## Page {page_content.page_number + 1}" )
        markdown_lines.append( "" )

        # Page text
        if page_content.text.strip():
            markdown_lines.append( "### Plain Text" )
            markdown_lines.append( page_content.text )
            markdown_lines.append( "" )

        # Images
        for image_info in page_content.images:
            markdown_lines.append( f"### Image {image_info.image_index + 1} [{image_info.size[0]}x{image_info.size[1]} @ position ({image_info.position[0]:.0f}, {image_info.position[1]:.0f})]" )
            markdown_lines.append( "" )

            # Image description
            if image_info.description.strip():
                markdown_lines.append( "#### Description" )
                markdown_lines.append( image_info.description )
                markdown_lines.append( "" )

            # OCR text
            if image_info.ocr_text.strip():
                markdown_lines.append( "#### OCR Text" )
                markdown_lines.append( f'"{image_info.ocr_text}"' )
                markdown_lines.append( "" )

        return '\n'.join( markdown_lines )


    def process_pdf( self, pdf_path: Path ) -> Tuple[List[PageContent], ProcessingMetrics]:
        """
        Process a PDF file completely with text extraction and Gemini image analysis.

        Requires:
            - pdf_path: Valid path to PDF file

        Ensures:
            - Returns list of PageContent objects and processing metrics
            - Extracts text from all pages
            - Processes all images with Gemini descriptions and OCR
            - Calculates accurate compression metrics

        Raises:
            - FileNotFoundError: If PDF file doesn't exist
            - Exception: If PDF processing fails
        """
        import time
        start_time = time.time()

        if not pdf_path.exists():
            raise FileNotFoundError( f"PDF file not found: {pdf_path}" )

        # Get original file size
        original_size = pdf_path.stat().st_size

        if self.debug:
            logger.debug( f"Processing PDF: {pdf_path.name} ({original_size / 1024 / 1024:.1f} MB)" )

        page_contents = []
        total_images = 0

        try:
            # Open PDF document
            doc = fitz.open( pdf_path )

            # Output PDF opening and basic info
            self._output( f"📄 Opened PDF: {len( doc )} pages", "verbose" )
            self._output( f"PDF has {len( doc )} pages", "debug" )
            self._output( "", "dot" )

            # Process each page
            for page_num in range( len( doc ) ):
                page = doc[page_num]

                # Output page processing progress
                self._output( f"📄 Processing page {page_num + 1}/{len( doc )}...", "verbose" )
                self._output( f"Processing page {page_num + 1}", "debug" )
                self._output( "", "dot" )

                # Extract text
                page_text = self._extract_page_text( page )

                # Extract images
                page_images = self._extract_page_images( page, page_num )
                total_images += len( page_images )

                # Output images found
                if page_images:
                    self._output( f"🖼️  Found {len( page_images )} image(s) on page {page_num + 1}", "verbose" )
                    self._output( f"Found {len( page_images )} images", "debug" )
                    for img in page_images:
                        self._output( "", "dot" )  # One dot per image

                # Process images with Gemini
                if page_images:
                    self._process_images_with_gemini( page_images )

                # Create page content
                page_content = PageContent(
                    page_number=page_num,
                    text=page_text,
                    images=page_images
                )

                # Generate markdown
                page_content.markdown = self._generate_page_markdown( page_content )

                page_contents.append( page_content )

            doc.close()

            # Calculate metrics
            processing_time = time.time() - start_time

            # Calculate text sizes
            text_only = '\n\n'.join( page.text for page in page_contents )
            text_only_bytes = len( text_only.encode( 'utf-8' ) )

            full_extraction = '\n\n'.join( page.markdown for page in page_contents )
            full_extraction_bytes = len( full_extraction.encode( 'utf-8' ) )

            compression_ratio = ( 1 - full_extraction_bytes / original_size ) * 100

            # Get Gemini usage stats
            gemini_stats = self.gemini_processor.get_usage_stats()

            metrics = ProcessingMetrics(
                original_size_bytes=original_size,
                text_only_bytes=text_only_bytes,
                full_extraction_bytes=full_extraction_bytes,
                compression_ratio=compression_ratio,
                pages_processed=len( page_contents ),
                images_found=total_images,
                processing_time_seconds=processing_time,
                gemini_tokens_used=gemini_stats["total_tokens_used"]
            )

            if self.debug:
                logger.debug( f"Processing complete: {metrics.compression_ratio:.1f}% compression" )

            return page_contents, metrics

        except Exception as e:
            logger.error( f"Failed to process PDF {pdf_path}: {e}" )
            raise


    def cleanup_temp_files( self ) -> None:
        """
        Clean up temporary image files.

        Requires:
            - None

        Ensures:
            - Removes all temporary image files created during processing
            - Does not affect other files in temp directory
        """
        try:
            for file_path in self.temp_dir.glob( "page_*_img_*.*" ):
                file_path.unlink()

            if self.debug:
                logger.debug( f"Cleaned up temporary files in {self.temp_dir}" )

        except Exception as e:
            logger.warning( f"Failed to cleanup temp files: {e}" )


if __name__ == "__main__":
    """Test the PDF processor when run directly."""
    import os
    from auth_checker import validate_credentials_or_exit

    # Validate credentials
    project_id = validate_credentials_or_exit()

    # Initialize Gemini processor
    gemini_processor = GeminiImageProcessor(
        project_id=project_id,
        debug=True,
        verbose=True
    )

    # Initialize PDF processor
    pdf_processor = PDFProcessor(
        gemini_processor=gemini_processor,
        debug=True,
        verbose=True
    )

    print( f"✅ PDF processor initialized successfully" )
    print( f"   Gemini model: {gemini_processor.model_name}" )
    print( f"   Temp directory: {pdf_processor.temp_dir}" )