"""Reuse v237 physics/scanner bytes; update execution metadata only."""
from pathlib import Path
import hashlib
import json
import os
import sys

HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent/'v237/newton_episode.py'
source = FROZEN.read_text()
before = "integration='v237', navigation='v232'"
assert source.count(before) == 1
source = source.replace(before, "integration='v241', navigation='v240'")
sys.path.insert(0, str(FROZEN.parent))
namespace = dict(__file__=str(FROZEN), __name__='v241_frozen_v237_recorder')
exec(compile(source, str(FROZEN), 'exec'), namespace)
if __name__ == '__main__':
    out = Path(os.environ['NEWTON_RUN_DIR'])
    (out/'v241_recorder_adapter.json').write_text(json.dumps(dict(
        frozen_v237_sha256=hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
        adapted_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        change='Execution metadata only; v237 recorder transformations and scanner deadline unchanged',
        navigation='v240', execution='v241', physics_steps_before_main=0), indent=2)+'\n')
    namespace['main']()
