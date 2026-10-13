"""Pack closed owned simulation evidence without deleting any source bytes."""
from pathlib import Path
import hashlib,json,os,tarfile,tempfile
roots=[Path('/private/tmp')/name for name in [
 'vla_nav2_simrepair_5z7q27y7','vla_newton_v100_eirtod60','vla_newton_v101_s8x5tb76',
 'vla_newton_v102_6laof2ks','vla_newton_v104_zdzl7tx0','vla_newton_v105_s_ar812x',
 'vla_newton_v106_ayonmr_7','vla_newton_v107_twn42v6t','vla_newton_v108_uuri27p6',
 'vla_newton_v109_bdvkg956','vla_newton_v110_6yoprj4j','vla_newton_v111_1x9kknab',
 'vla_newton_v111_r7x6wgev','vla_newton_v113_v96bqp38','vla_newton_v114_m42gyqka']]
out=Path(tempfile.mkdtemp(prefix='vla_simrepair_archive_',dir='/private/tmp'))
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
members={}
for root in roots:
 assert root.is_dir() and root.parent==Path('/private/tmp')
 for p in sorted(root.rglob('*')):
  name=str(p.relative_to(root.parent))
  if p.is_symlink():members[name]={'kind':'symlink','target':os.readlink(p)}
  elif p.is_file():members[name]={'kind':'file','bytes':p.stat().st_size,'sha256':sha(p)}
manifest=out/'member_manifest.json';manifest.write_text(json.dumps(members,indent=2)+'\n')
archive=out/'vla_nav2_sim_repair_v100_v114.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=3) as stream:
 for root in roots:stream.add(root,arcname=root.name,recursive=True)
 stream.add(manifest,arcname='member_manifest.json')
verified=0
with tarfile.open(archive,'r|gz') as stream:
 for item in stream:
  if item.isdir() or item.name=='member_manifest.json':continue
  expected=members[item.name]
  if item.issym():assert expected=={'kind':'symlink','target':item.linkname}
  else:
   assert item.isfile() and item.size==expected['bytes']
   assert hashlib.file_digest(stream.extractfile(item),'sha256').hexdigest()==expected['sha256'],item.name
  verified+=1
assert verified==len(members)
receipt={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),
 'member_manifest_sha256':sha(manifest),'verified_members':verified,'roots':[str(p) for p in roots],
 'deleted_sources':False,'execution_image_included':False,
 'execution_image_retained_local':'sha256:d4aec648bd283fba07aa3a76724b53df69d3ee7a9ffbf08776bd835858729343'}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
