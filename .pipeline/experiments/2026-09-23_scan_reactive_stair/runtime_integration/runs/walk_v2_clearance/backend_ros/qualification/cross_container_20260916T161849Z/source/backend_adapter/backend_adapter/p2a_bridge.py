"""Import helper for the accepted P2A lifecycle core without editing it."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType
from typing import Optional

_MODULE = None  # type: Optional[ModuleType]


def load_p2a_core() -> ModuleType:
    global _MODULE
    if _MODULE is not None:
        return _MODULE
    here = pathlib.Path(__file__).resolve()
    experiment_root = here.parents[2]
    core_path = experiment_root / "navigation_service" / "core.py"
    if not core_path.is_file():
        raise RuntimeError("p2a_core_missing:%s" % core_path)
    spec = importlib.util.spec_from_file_location("p2a_navigation_service_core", str(core_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("p2a_core_import_spec_failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    _MODULE = module
    return module
