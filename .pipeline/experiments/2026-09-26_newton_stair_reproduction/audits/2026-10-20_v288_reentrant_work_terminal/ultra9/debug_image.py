from pathlib import Path
import subprocess,json,time
R=Path('/home/ubuntu/sun/vla_v288_20261020')
log=R/'evidence/debug_image01.log'
with log.open('x') as f:code=subprocess.run(['docker','build','-f',str(R/'migration/Dockerfile.debug'),'-t','vla-v288-foxy:debug01',str(R/'migration')],stdout=f,stderr=subprocess.STDOUT).returncode
image=subprocess.check_output(['docker','image','inspect','vla-v288-foxy:debug01','--format','{{.Id}}'],text=True).strip() if not code else None
(R/'evidence/debug_image01.json').write_text(json.dumps(dict(passed=code==0,returncode=code,image=image,scope='Task-owned debugger image; no host-wide settings'),indent=2)+'\n')
raise SystemExit(code)
