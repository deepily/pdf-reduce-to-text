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
Gemini 2.5 Flash client for image description and OCR processing.

Based on existing Gemini client patterns from:
- apps/minimalist-chained/services/gemini_client.py
- apps/minimalist-chained/services/alternative_voice_ai.py

Uses the latest Gemini 2.5 Flash model for optimal image processing and OCR.

Requires:
    - Valid Google Cloud credentials
    - Project ID and location configured
    - google-genai package installed

Ensures:
    - High-quality image descriptions
    - Accurate OCR text extraction
    - Rate limiting and error handling
    - Token usage tracking
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import io
import base64

from google import genai
from PIL import Image
import google.auth


logger = logging.getLogger( __name__ )


class GeminiImageProcessor:
    """
    Gemini 2.5 Flash client for image description and OCR processing.

    Uses the latest Gemini 2.5 Flash model with thinking capabilities
    for high-quality image analysis and text extraction.
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-2.5-flash",
        debug: bool = False,
        verbose: bool = False
    ):
        """
        Initialize Gemini client with Vertex AI.

        Requires:
            - project_id: Valid GCP project ID
            - location: GCP region (default: us-central1)
            - model_name: Gemini model to use (default: gemini-2.5-flash)
            - debug: Enable debug logging
            - verbose: Enable verbose progress output

        Ensures:
            - Client is properly initialized and authenticated
            - Model configuration is validated
            - Ready for image processing requests
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.debug = debug
        self.verbose = verbose

        # Token usage tracking
        self.total_tokens_used = 0
        self.request_count = 0

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

        # Output tracking for dot mode
        self.dots_printed = False

        if debug:
            logger.setLevel( logging.DEBUG )
            logger.debug( f"Initializing Gemini client with model: {model_name}" )

        try:
            # Initialize the Vertex AI client (following existing pattern)
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location
            )

            if debug:
                logger.debug( f"Gemini client initialized successfully" )
                logger.debug( f"Project: {project_id}, Location: {location}" )

        except Exception as e:
            logger.error( f"Failed to initialize Gemini client: {e}" )
            raise


    def test_connection( self ) -> bool:
        """
        Test connection to Gemini API with a simple request.

        Requires:
            - Client is initialized
            - Valid authentication credentials

        Ensures:
            - Returns True if API is accessible
            - Returns False if connection fails
            - Logs connection status

        Raises:
            - Does not raise exceptions - handles all errors gracefully
        """
        try:
            if self.debug:
                logger.debug( "Testing Gemini API connection..." )

            # Make a simple test request
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Test connection. Reply with 'OK'."
            )

            if response and response.text:
                if self.debug:
                    logger.debug( "✓ Gemini API connection test successful" )
                return True
            else:
                if self.debug:
                    logger.debug( "❌ Gemini API returned empty response" )
                return False

        except Exception as e:
            if self.debug:
                logger.debug( f"❌ Gemini API connection test failed: {e}" )
            return False


    def _prepare_image( self, image_path: Path, max_dimension: int = 1024 ) -> bytes:
        """
        Prepare image for Gemini processing.

        Requires:
            - image_path: Valid path to image file
            - max_dimension: Maximum width/height (default: 1024)

        Ensures:
            - Returns image as bytes in optimal format
            - Resizes large images to save tokens
            - Maintains aspect ratio during resize

        Raises:
            - FileNotFoundError: If image file doesn't exist
            - ValueError: If image cannot be processed
        """
        if not image_path.exists():
            raise FileNotFoundError( f"Image not found: {image_path}" )

        try:
            with Image.open( image_path ) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert( "RGB" )

                # Resize if too large
                if max( img.size ) > max_dimension:
                    img.thumbnail( ( max_dimension, max_dimension ), Image.Resampling.LANCZOS )
                    if self.debug:
                        logger.debug( f"Resized image to {img.size}" )

                # Convert to bytes
                img_bytes = io.BytesIO()
                img.save( img_bytes, format="JPEG", quality=85 )
                return img_bytes.getvalue()

        except Exception as e:
            raise ValueError( f"Failed to process image {image_path}: {e}" )


    def _rate_limit( self ):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            sleep_time = self.min_request_interval - elapsed
            if self.verbose:
                print( f"⏱️  Rate limiting delay ({int(sleep_time*1000)}ms)...", flush=True )
            time.sleep( sleep_time )
        self.last_request_time = time.time()


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


    def generate_image_description( self, image_path: Path, custom_prompt: Optional[str] = None ) -> str:
        """
        Generate detailed description of an image using Gemini 2.5 Flash.

        Requires:
            - image_path: Valid path to image file
            - custom_prompt: Optional custom prompt (uses default if None)

        Ensures:
            - Returns detailed, contextual image description
            - Focuses on text content, diagrams, and important visual elements
            - Suitable for context window stuffing

        Raises:
            - FileNotFoundError: If image file doesn't exist
            - Exception: If API call fails
        """
        self._rate_limit()

        # Default prompt optimized for context window stuffing
        if custom_prompt is None:
            prompt = """
            Analyze this image and provide a detailed description that would be useful for someone who cannot see the image. Focus on:

            1. **Text content**: Any visible text, labels, titles, captions
            2. **Document structure**: Headers, sections, layout elements
            3. **Visual elements**: Charts, diagrams, graphs, tables
            4. **Context**: What type of document/content this appears to be
            5. **Key information**: Most important data or concepts shown

            Be concise but comprehensive. This description will be used for text-based AI processing.
            """
        else:
            prompt = custom_prompt

        try:
            # Prepare image
            image_bytes = self._prepare_image( image_path )

            # Output progress indication
            self._output( f"🤖 Generating description for {image_path.name}...", "verbose" )
            self._output( f"Generating description for {image_path.name}", "debug" )
            self._output( "", "dot" )

            # Create the request
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            { "text": prompt },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64.b64encode( image_bytes ).decode( "utf-8" )
                                }
                            }
                        ]
                    }
                ]
            )

            # Track usage
            self.request_count += 1
            if hasattr( response, 'usage_metadata' ) and response.usage_metadata:
                tokens = response.usage_metadata.total_token_count or 0
                self.total_tokens_used += tokens
                if self.debug:
                    logger.debug( f"Used {tokens} tokens for description" )

            description = response.text.strip()

            if self.debug:
                logger.debug( f"Generated description: {description[:100]}..." )

            return description

        except Exception as e:
            logger.error( f"Failed to generate description for {image_path}: {e}" )
            raise


    def extract_text_from_image( self, image_path: Path ) -> str:
        """
        Extract text from image using Gemini 2.5 Flash OCR capabilities.

        Requires:
            - image_path: Valid path to image file

        Ensures:
            - Returns extracted text as clean string
            - Preserves text structure and formatting where possible
            - Handles various text orientations and fonts

        Raises:
            - FileNotFoundError: If image file doesn't exist
            - Exception: If API call fails
        """
        self._rate_limit()

        # OCR-specific prompt
        prompt = """
        Extract ALL visible text from this image. Preserve the original structure and formatting as much as possible.

        Guidelines:
        - Include headers, body text, captions, labels
        - Maintain line breaks and paragraph structure
        - If text is in tables, preserve table structure
        - Include any numbers, dates, or special characters
        - If text is unclear or partially obscured, indicate with [unclear] or [partial]

        Return only the extracted text, no additional commentary.
        """

        try:
            # Prepare image
            image_bytes = self._prepare_image( image_path )

            # Output progress indication
            self._output( f"📝 Extracting OCR text from {image_path.name}...", "verbose" )
            self._output( f"Extracting text from {image_path.name}", "debug" )
            self._output( "", "dot" )

            # Create the request
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            { "text": prompt },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64.b64encode( image_bytes ).decode( "utf-8" )
                                }
                            }
                        ]
                    }
                ]
            )

            # Track usage
            self.request_count += 1
            if hasattr( response, 'usage_metadata' ) and response.usage_metadata:
                tokens = response.usage_metadata.total_token_count or 0
                self.total_tokens_used += tokens
                if self.debug:
                    logger.debug( f"Used {tokens} tokens for OCR" )

            extracted_text = response.text.strip()

            if self.debug:
                logger.debug( f"Extracted text: {extracted_text[:100]}..." )

            return extracted_text

        except Exception as e:
            logger.error( f"Failed to extract text from {image_path}: {e}" )
            raise


    def get_usage_stats( self ) -> Dict[str, Any]:
        """
        Get current usage statistics.

        Requires:
            - None

        Ensures:
            - Returns dictionary with token usage and request counts
            - Includes model information and timing
        """
        return {
            "model": self.model_name,
            "total_tokens_used": self.total_tokens_used,
            "request_count": self.request_count,
            "project_id": self.project_id,
            "location": self.location
        }


if __name__ == "__main__":
    """Test the Gemini client when run directly."""
    import os
    from auth_checker import validate_credentials_or_exit

    # Validate credentials
    project_id = validate_credentials_or_exit()

    # Initialize client
    processor = GeminiImageProcessor(
        project_id=project_id,
        debug=True,
        verbose=True
    )

    print( f"✅ Gemini 2.5 Flash client initialized successfully" )
    print( f"   Model: {processor.model_name}" )
    print( f"   Project: {processor.project_id}" )
    print( f"   Location: {processor.location}" )