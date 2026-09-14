"""
MLPMP Full Suite v2.0.4 - Root Launcher Entrypoint.
Redirects execution to suite/ architecture.
"""
import os
import sys
from pathlib import Path

suite_dir = Path(__file__).resolve().parent / "suite"
sys.path.insert(0, str(suite_dir))
os.chdir(str(suite_dir))

from run import main

if __name__ == "__main__":
    main()
