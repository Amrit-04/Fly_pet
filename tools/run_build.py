"""Offline simulation script to generate circuit artifacts without shell execution."""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from tools.build_mock_circuit import main as build_main

if __name__ == "__main__":
    build_main()
