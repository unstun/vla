"""Reuse original bounded supervision and retention at an external render root."""
import importlib.util
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]


def temporary_root():
    root = Path(os.environ['V118_RENDER_ROOT'])
    if root.resolve() != root or root.parent != Path('/private/tmp') or not root.name.startswith('vla_newton_v118_'):
        raise ValueError('Expected an owned external temporary render root')
    return root


def supervise():
    source = BASE.parent / '2026-09-26_newton_macos_policy/scripts/run_bounded.py'
    spec = importlib.util.spec_from_file_location('original_render_supervisor', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.BASE = temporary_root()
    module.MAX_DEADLINE_S = 1800
    module.main()


def main():
    from render_capture import verify_manifest
    verify_manifest('v118')
    root = temporary_root()
    scripts = root / 'scripts'
    scripts.mkdir()
    (scripts / 'run_bounded.py').write_text(
        'import sys\n'
        'sys.path.insert(0, ' + repr(str(HERE)) + ')\n'
        'from run_review import supervise\n'
        'supervise()\n')
    sys.path.insert(0, str(BASE / 'versions/v51'))
    import managed_run
    managed_run.a.BASE = root
    managed_run.a.AUDIT = root / 'artifact_audit'
    return managed_run.main()


if __name__ == '__main__':
    raise SystemExit(main())
