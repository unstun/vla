"""Reuse the bounded supervisor with an explicitly owned temporary root."""
import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
source = BASE.parent / "2026-09-26_newton_macos_policy/scripts/run_bounded.py"
root = Path(os.environ["V179_TEMP_ROOT"]).resolve()
if root.parent != Path("/private/tmp") or root.name != "vla_policy_stop_20261012":
    raise ValueError("Undeclared temporary root")
spec = importlib.util.spec_from_file_location("v179_original_supervisor", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.BASE = root
module.main()
