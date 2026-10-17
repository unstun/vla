"""Reuse the qualified local process supervisor with this experiment root."""
import importlib.util
from pathlib import Path

base = Path(__file__).resolve().parents[1]
source = base.parent / "2026-09-26_newton_macos_policy/scripts/run_bounded.py"
spec = importlib.util.spec_from_file_location("newton_qualified_supervisor", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.BASE = base
module.main()
