"""Verify inherited source fixtures without writing any linked parent file."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'source_surface_precompute_v272/native'
m=json.loads((HERE.parent/'v271/results/fixture_files.json').read_text())
for rel,h in m.items():assert hashlib.sha256((WORK/rel).read_bytes()).hexdigest()==h,rel
print(json.dumps(dict(inherited_fixture_files=len(m),mismatches=0)))
