"""Original v233 package/interface gate with all 14 prefixes rebound to this rebuild."""
from pathlib import Path

FROZEN = Path(__file__).resolve().parent.parent / 'v233/preflight.py'
# /migration is a short mount, so locate its sibling using the actual repository.
if not FROZEN.is_file():
    import json
    prefix = Path(json.loads((Path(__file__).parent / 'binding.json').read_text())['remote_root'])
    FROZEN = prefix / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v233/preflight.py'
source = FROZEN.read_text()
before = "expected='/work/install/'+name if name in rebuilt else reference[name]"
assert source.count(before) == 1
source = source.replace(before, "expected='/work/install/'+name")
namespace = {'__file__': str(FROZEN), '__name__': 'v234_frozen_preflight'}
exec(compile(source, str(FROZEN), 'exec'), namespace)
