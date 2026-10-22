from pathlib import Path
import subprocess,json,hashlib
R=Path('/home/ubuntu/sun/vla_v288_20261020');image='sha256:af529e408d9d130ba7b15a1eb2b78dc7b5408953a0de994ea05cccb43972fbec'
assert subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True).strip()==image
(R/'evidence/debug_image01.json').write_text(json.dumps(dict(passed=True,image=image,reused_from='v287 task-owned debugger image',dockerfile_sha256=hashlib.sha256((R/'migration/Dockerfile.debug').read_bytes()).hexdigest(),physics_steps=0),indent=2)+'\n')
