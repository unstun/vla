from pathlib import Path
import json,shutil,subprocess,os
R=Path('/home/ubuntu/sun/vla_v288_20261020')
failed=R/'preflight_failed/A04_01';failed.mkdir(parents=True)
source=R/'physical_runs/v288_A04_preflight01';assert source.exists()
shutil.move(str(source),str(failed/source.name))
shutil.copy2(R/'evidence/physical_preflight_progress.json',failed/'progress.json')
(R/'evidence/profile_metadata_binding01.json').write_text(json.dumps(dict(physics_steps=0,source_manifest_changed=False,navigation_changed=False,correction='Verifier view supplies the two unchanged inherited geometry metadata fields; same actual field and numerical checks',failed_preflight_preserved=str(failed)),indent=2)+'\n')
subprocess.run(['python3',str(R/'migration/batch.py'),'preflight'],env=dict(os.environ,V288_PREFLIGHT_ID='02'),check=True)
subprocess.run(['python3',str(R/'migration/physical_setup.py'),'freeze'],check=True)
print('Ten zero-step preflights passed; execution frozen and waiting for local return',flush=True)
