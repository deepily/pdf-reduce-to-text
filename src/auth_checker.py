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
GCP credential validation module.

Based on existing auth checking patterns from:
- apps/frontend/test_gemini_connection.py
- apps/frontend/test_gemini_live.py

Requires:
    - Google Cloud credentials are properly configured
    - PROJECT_ID is set in environment or available from credentials

Ensures:
    - Returns valid project_id if authentication succeeds
    - Provides clear error messages for auth failures
    - Exits gracefully with helpful instructions
"""

import os
import sys
from typing import Optional, Tuple


def check_gcp_credentials() -> Optional[str]:
    """
    Test Google Cloud authentication and return project ID.

    Requires:
        - Valid Google Cloud credentials (via ADC or service account)
        - PROJECT_ID environment variable OR project from credentials

    Ensures:
        - Returns project_id string if authentication succeeds
        - Returns None if authentication fails
        - Prints clear error messages with remediation steps

    Raises:
        - Does not raise exceptions - handles all errors gracefully
    """
    try:
        import google.auth
        credentials, project = google.auth.default()

        if not credentials:
            print( "❌ No Google Cloud credentials found" )
            print( "→ Set GOOGLE_APPLICATION_CREDENTIALS or use gcloud auth" )
            return None

        # Try to get project ID from credentials first, then environment
        project_id = project or os.getenv( "PROJECT_ID" )

        if not project_id:
            print( "❌ PROJECT_ID not found in credentials or environment" )
            print( "→ Please set PROJECT_ID environment variable" )
            print( "→ Or run: gcloud auth application-default login" )
            return None

        print( f"✓ Google Cloud credentials found" )
        if project:
            print( f"✓ Default project from credentials: {project_id}" )
        else:
            print( f"✓ Using PROJECT_ID from environment: {project_id}" )

        return project_id

    except ImportError as e:
        print( f"❌ Failed to import google.auth: {e}" )
        print( "→ Install required packages: pip install google-auth" )
        return None

    except Exception as e:
        print( f"❌ Authentication error: {e}" )
        print( "→ Ensure you have authenticated with Google Cloud" )
        print( "→ Run: gcloud auth application-default login" )
        return None


def validate_credentials_or_exit( test_api: bool = True ) -> str:
    """
    Validate GCP credentials and optionally test API connection, exit if not valid.

    Requires:
        - Valid Google Cloud authentication
        - Accessible project ID
        - test_api: Whether to test actual API connection (default: True)

    Ensures:
        - Returns project_id if validation succeeds
        - Exits program with status 1 if validation fails
        - Tests actual API connectivity if test_api=True
        - Provides clear error messages and remediation steps

    Raises:
        - SystemExit(1) if credentials are invalid or API test fails
    """
    project_id = check_gcp_credentials()

    if not project_id:
        print( "\n💡 To fix authentication issues:" )
        print( "1. Run: gcloud auth application-default login" )
        print( "2. Set PROJECT_ID environment variable" )
        print( "3. Or set GOOGLE_APPLICATION_CREDENTIALS to service account key" )
        sys.exit( 1 )

    # Test actual API connection
    if test_api:
        location = get_gcp_location()
        if not test_gemini_api_connection( project_id, location ):
            print( "\n💡 To fix API connection issues:" )
            print( "1. Run: gcloud auth application-default login" )
            print( "2. Ensure Vertex AI API is enabled in Google Cloud Console" )
            print( "3. Verify your account has Vertex AI User role" )
            print( "4. Check network connectivity" )
            sys.exit( 1 )

    return project_id


def test_gemini_api_connection( project_id: str, location: str ) -> bool:
    """
    Test actual Gemini API connection by making a simple request.

    Requires:
        - project_id: Valid GCP project ID
        - location: Valid GCP location
        - Active authentication credentials

    Ensures:
        - Returns True if API is accessible and working
        - Returns False if API call fails
        - Prints clear error messages for failures

    Raises:
        - Does not raise exceptions - handles all errors gracefully
    """
    try:
        print( "   Testing Gemini API connection..." )

        from google import genai
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )

        # Make a simple test request to verify API access
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Test connection. Reply with 'OK'."
        )

        if response and response.text:
            print( "✓ Gemini API connection successful" )
            return True
        else:
            print( "❌ Gemini API returned empty response" )
            return False

    except ImportError as e:
        print( f"❌ Failed to import google.genai: {e}" )
        print( "→ Install required packages: pip install google-genai" )
        return False

    except Exception as e:
        error_msg = str( e ).lower()

        if "reauthentication" in error_msg or "auth" in error_msg:
            print( f"❌ Authentication failed: {e}" )
            print( "→ Run: gcloud auth application-default login" )
        elif "permission" in error_msg or "forbidden" in error_msg:
            print( f"❌ Permission denied: {e}" )
            print( "→ Ensure Vertex AI API is enabled in your project" )
            print( "→ Check that your account has proper permissions" )
        elif "not found" in error_msg or "invalid" in error_msg:
            print( f"❌ Invalid project or model: {e}" )
            print( f"→ Verify project ID: {project_id}" )
            print( f"→ Verify location: {location}" )
        else:
            print( f"❌ API connection test failed: {e}" )
            print( "→ Check network connectivity and project configuration" )

        return False


def get_gcp_location() -> str:
    """
    Get GCP location from environment or use default.

    Requires:
        - None (uses sensible default)

    Ensures:
        - Returns valid GCP location string
        - Uses us-central1 as default (widely available)
    """
    return os.getenv( "GOOGLE_CLOUD_LOCATION", "us-central1" )


if __name__ == "__main__":
    """Test authentication when run directly."""
    print( "Testing Google Cloud authentication..." )
    project_id = check_gcp_credentials()

    if project_id:
        location = get_gcp_location()
        print( f"\n✅ Authentication successful!" )
        print( f"   Project: {project_id}" )
        print( f"   Location: {location}" )

        # Test API connectivity
        if test_gemini_api_connection( project_id, location ):
            print( f"\n✅ Full authentication and API test successful!" )
        else:
            print( f"\n❌ API connection test failed!" )
            sys.exit( 1 )
    else:
        print( f"\n❌ Authentication failed!" )
        sys.exit( 1 )