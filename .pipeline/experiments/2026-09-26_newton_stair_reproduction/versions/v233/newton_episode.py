"""Select v216 locomotion, then execute the unchanged v198 physical recorder."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
VERSIONS = HERE.parent


def activate():
    path = VERSIONS / 'v216/activate.py'
    spec = importlib.util.spec_from_file_location('v219_locomotion_activation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    adapter = module.install()
    assert adapter.SOURCE.resolve() == (VERSIONS / 'v216/stance_hold.py').resolve()
    return adapter


def main():
    adapter = activate()
    out = Path(os.environ['NEWTON_RUN_DIR'])
    files = [Path(adapter.__file__), adapter.SOURCE, VERSIONS / 'v216/activate.py',
             VERSIONS / 'v198/newton_episode.py', Path(__file__)]
    (out / 'locomotion_activation.json').write_text(json.dumps({
        'integration': 'v233', 'navigation': 'v232', 'locomotion': 'v216',
        'files': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        'adapter_loaded_before_robot_construction': True,
    }, indent=2) + '\n')
    runpy.run_path(str(VERSIONS / 'v198/newton_episode.py'), run_name='__main__')


if __name__ == '__main__':
    main()
