from pathlib import Path
import shutil, json, hashlib
ROOT=Path('/home/ubuntu/sun/vla_v289_20261020')
PARENT=Path('/home/ubuntu/sun/vla_v288_20261020')
ROOT.mkdir(exist_ok=True)
assert not (ROOT/'repo').exists()
shutil.copytree(PARENT/'repo',ROOT/'repo')
(ROOT/'evidence').mkdir()
(ROOT/'native').mkdir()
for name in ('dependencies','fixtures','component_fixtures03'):
 shutil.copytree(PARENT/'native'/name,ROOT/'native'/name)
for name in ('cohort','profile_reference','environment_score_v224'):
 shutil.copytree(PARENT/name,ROOT/name)
(ROOT/'geometry_data').symlink_to(PARENT/'geometry_data',target_is_directory=True)
(ROOT/'source_v224').mkdir()
work=ROOT/'bridge248/native';work.mkdir(parents=True)
shutil.copytree(PARENT/'bridge248/native/src',work/'src')
shutil.copy2(PARENT/'bridge248/native/source_inventory.json',work/'source_inventory.json')
print('Private v289 workspace prepared; v288 data unchanged')
