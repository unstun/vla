"""Return compact negative/control evidence without accepting a candidate."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for version,folder in [('v274','gpmp_endpoint_physics_v274'),('v277','gpmp_fixed_boundary_v277'),('v278','source_free_index_v278')]:
 source=BASE/folder;dest=HERE/'development'/version;dest.mkdir(parents=True,exist_ok=True);returned={}
 inputs=list(source.glob('*.log'))+list((source/'evaluation').glob('controls*/*/metrics.txt'))+list((source/'evaluation').glob('controls*/receipt.json'))+list((source/'evaluation').glob('legacy_requests_*/receipt.json'))+list((source/'native/regressions').glob('*.xml'))+list((source/'native/build/lite3_nav2_plugins/test_results').rglob('*.xml'))
 for p in inputs:
  rel=str(p.relative_to(source));assert p.stat().st_size<8*1024*1024
  q=dest/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);returned[rel]=dict(sha256=sha(p),bytes=p.stat().st_size,remote_path=str(p))
 inv=source/'native/source_inventory.json';q=dest/'source_inventory.json';shutil.copy2(inv,q);returned['source_inventory.json']=dict(sha256=sha(inv),bytes=inv.stat().st_size,remote_path=str(inv))
 (dest/'return_inventory.json').write_text(json.dumps(dict(version=version,accepted_for_matrix=False,accepted_for_physics=False,returned=returned),indent=2)+'\n')
 print(json.dumps(dict(version=version,files=len(returned),bytes=sum(r['bytes'] for r in returned.values()))))
