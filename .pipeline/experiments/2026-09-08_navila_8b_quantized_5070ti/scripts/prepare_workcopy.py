"""Rebuild an auditable inference-only compatibility copy of pinned NaVILA."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1]).resolve()
root = Path(sys.argv[2]).resolve()
target = root/'work/NaVILA'
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('.git','__pycache__','assets','.github'))
edits = []

def replace(path, old, new, count=1):
    file=target/path
    before=file.read_text()
    assert before.count(old)==count, (path,old,before.count(old))
    after=before.replace(old,new)
    file.write_text(after)
    edits.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
                                     fromfile='a/'+path,tofile='b/'+path))

# DeepSpeed is only used when explicitly initializing sequence-parallel groups.
# Keep those paths functional but avoid requiring the training runtime to import.
path='llava/train/sequence_parallel/globals.py'
replace(path,'import deepspeed.comm as dist\n','')
replace(path,'    def __init__(self, ulysses_degree, ring_degree, dp_degree, use_ulysses_low, ring_type):\n',
        '    def __init__(self, ulysses_degree, ring_degree, dp_degree, use_ulysses_low, ring_type):\n        import deepspeed.comm as dist\n')
# Remaining distributed calls are in set_pg_manager; insert below its signature.
file=target/path
before=file.read_text()
import ast
node=next(n for n in ast.parse(before).body if isinstance(n,ast.FunctionDef) and n.name=='set_pg_manager')
lines=before.splitlines(True)
lines.insert(node.body[0].lineno-1,'    import deepspeed.comm as dist\n')
after=''.join(lines);file.write_text(after)
edits.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path))

# Lazy-import unselected vision encoders; InternViT imports FlashAttention.
path='llava/model/multimodal_encoder/builder.py'
replace(path,'from .intern_encoder import InternVisionTower, InternVisionTowerS2\n','')
replace(path,'    if "intern" in vision_tower_name.lower():\n',
        '    if "intern" in vision_tower_name.lower():\n        from .intern_encoder import InternVisionTower, InternVisionTowerS2\n')
replace(path,'from .radio_encoder import RADIOVisionTower\n','')
replace(path,'    elif "radio" in vision_tower_name:\n',
        '    elif "radio" in vision_tower_name:\n        from .radio_encoder import RADIOVisionTower\n')

# Multiscale wrapper is only required by the S2 encoder, absent in this model.
path='llava/model/multimodal_encoder/vision_encoder.py'
replace(path,'from s2wrapper import forward as multiscale_forward\n','')
file=target/path;before=file.read_text();tree=ast.parse(before)
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='VisionTowerS2')
fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='forward')
lines=before.splitlines(True);lines.insert(fn.body[0].lineno-1,'        from s2wrapper import forward as multiscale_forward\n')
after=''.join(lines);file.write_text(after)
edits.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path))

setup=root/'setup';setup.mkdir(exist_ok=True)
(setup/'compatibility.patch').write_text(''.join(edits))
manifest=[]
for path in sorted(target.rglob('*')):
    if path.is_file() and '__pycache__' not in path.parts:
        manifest.append({'path':path.relative_to(target).as_posix(),
                         'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(setup/'work_source_manifest.json').write_text(json.dumps({'files':manifest},indent=2))
print(f'Prepared {len(manifest)} files at {target}')
