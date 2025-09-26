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
Convenience wrapper to run the PDF Context Window Stuffing CLI from project root.

This allows running the CLI tool using:
    python reduce_to_text.py report
    python reduce_to_text.py process --verbose
    python reduce_to_text.py status

Alternative execution methods:
    python -m src report
    python src/reduce_to_text.py report
"""

from src.reduce_to_text import cli

if __name__ == "__main__":
    cli()