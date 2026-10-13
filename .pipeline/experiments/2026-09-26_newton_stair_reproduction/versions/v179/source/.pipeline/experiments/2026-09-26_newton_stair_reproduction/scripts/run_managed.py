"""Default artifact-aware entry point; preserve all historical launchers."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'versions/v51'))
from managed_run import main

if __name__=='__main__':raise SystemExit(main())
