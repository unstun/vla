"""Use the original bounded supervisor with an explicit temporary run root."""
from pathlib import Path
import importlib.util,os
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
source=BASE.parent/'2026-09-26_newton_macos_policy/scripts/run_bounded.py'
spec=importlib.util.spec_from_file_location('v64_original_supervisor',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.BASE=Path(os.environ['V64_TEMP_ROOT'])
module.MAX_DEADLINE_S=1800
module.main()
