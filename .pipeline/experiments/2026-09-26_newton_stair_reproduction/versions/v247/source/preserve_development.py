from pathlib import Path
import hashlib,json,os,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'physical_traversability_v247/native'
OUT=BASE/'physical_traversability_v247/evaluation'/os.environ.get('V247_SNAPSHOT_TAG','development02_source');OUT.mkdir(exist_ok=False)
owned={str(p.relative_to(HERE)):hashlib.sha256((WORK/p.relative_to(HERE)).read_bytes()).hexdigest() for p in (HERE/'src').rglob('*') if p.is_file()}
for rel in owned:
 q=OUT/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(WORK/rel,q)
shutil.copy2(WORK/'source_inventory.json',OUT/'source_inventory.json')
installed={str(p.relative_to(WORK)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (WORK/'install').rglob('*') if p.is_file() and p.suffix!='.pyc'}
(OUT/'installed_files.json').write_text(json.dumps(installed,indent=2)+'\n')
(OUT/'owned_source.json').write_text(json.dumps(owned,indent=2)+'\n')
