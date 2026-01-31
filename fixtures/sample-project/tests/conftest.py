"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Add src to Python path for imports
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))
