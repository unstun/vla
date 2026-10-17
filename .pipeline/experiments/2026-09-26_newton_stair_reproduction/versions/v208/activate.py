"""Explicitly select the versioned locomotion adapter before robot construction."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def install():
    path = HERE / 'newton_stance.py'
    existing = sys.modules.get('newton_stance')
    if existing is not None:
        if Path(existing.__file__).resolve() != path:
            raise RuntimeError('Select v208 before constructing or importing a different stance adapter')
        return existing
    spec = importlib.util.spec_from_file_location('newton_stance', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules['newton_stance'] = module
    return module
