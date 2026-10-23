"""Paths and identities for one fixed same-host paired physical campaign."""
from pathlib import Path
import hashlib,importlib.util,json,os
CAMPAIGN=Path('/home/ubuntu/sun/vla_v291_pair24_20261022')
BINDING=CAMPAIGN/'source'
OLD=Path('/home/ubuntu/sun/vla_v290_20261021')
NEW=Path('/home/ubuntu/sun/vla_v291_20261022')
ROOT=OLD/'repo'
EXP=ROOT/'.pipeline/experiments/2026-09-26_newton_stair_reproduction'
VERSIONS=EXP/'versions'
VARIANT=os.environ.get('PAIR_VARIANT','v290')
assert VARIANT in ('v290','v291')
VERSION_ROOT=OLD if VARIANT=='v290' else NEW
STANCE=VERSIONS/'v216' if VARIANT=='v290' else NEW/'source'
LOCOMOTION_NAME='v216' if VARIANT=='v290' else 'v291'
os.environ['V291_PARENT_STANCE']=str(VERSIONS/'v216/stance_hold.py')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def verify():
 for root in (OLD,NEW):
  m=json.loads((root/'source/native_manifest.json').read_text())
  assert json.loads((root/'benchmark/offline_gate.json').read_text())['passed']
  for rel,h in m['source_files'].items():assert sha(root/'source'/rel)==h,(root,rel)
  for rel,h in m['installed_files'].items():assert sha(root/'native'/rel)==h,(root,rel)
 manifest=BINDING/'campaign_manifest.json'
 if manifest.exists():
  for path,h in json.loads(manifest.read_text())['files'].items():assert sha(path)==h,path
 return dict(passed=True,navigation=VARIANT,locomotion=LOCOMOTION_NAME,
             native_manifest_sha256=sha(VERSION_ROOT/'source/native_manifest.json'),
             stance_sha256=sha(STANCE/'stance_hold.py'),adapter_sha256=sha(STANCE/'newton_stance.py'),
             physical_manifest_sha256=sha(manifest) if manifest.exists() else None)
