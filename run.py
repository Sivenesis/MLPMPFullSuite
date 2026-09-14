"""
MLPMP Full Suite v2.0.4 - Root Launcher Entrypoint.
Redirects execution to version2 architecture.
"""
import os
import sys
from pathlib import Path

v2_dir = Path(__file__).resolve().parent / "version2"
sys.path.insert(0, str(v2_dir))
os.chdir(str(v2_dir))

from run import main

if __name__ == "__main__":
    main()
