"""Use original managed retention while keeping bulk outside the repository."""
from pathlib import Path
import os,sys
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
sys.path.insert(0,str(BASE/'versions/v51'))
import managed_run
managed_run.a.BASE=Path(os.environ['V64_TEMP_ROOT'])
managed_run.a.AUDIT=managed_run.a.BASE/'artifact_audit'
raise SystemExit(managed_run.main())
