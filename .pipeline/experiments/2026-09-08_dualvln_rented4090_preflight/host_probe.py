
import json,subprocess,os
from pathlib import Path

def run(argv):
 p=subprocess.run(argv,capture_output=True,text=True,timeout=15)
 return {'exit':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
result={
 'host':run(['hostname']),
 'os':Path('/etc/os-release').read_text(),
 'python':run(['python3','--version']),
 'gpu':run(['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu,driver_version','--format=csv,noheader']),
 'compute_processes':run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader']),
 'gpu_process_sample':run(['nvidia-smi','pmon','-c','1']),
 'disk':run(['df','-h','/','/home']),
 'memory':run(['free','-h']),
 'home_entries':sorted(p.name for p in Path.home().iterdir() if not p.name.startswith('.')),
 'environment_roots':{},
}
for base in [Path.home()/'miniconda3/envs',Path.home()/'anaconda3/envs',Path.home()/'.venvs',Path('/opt/conda/envs'),Path('/data')]:
 if base.is_dir(): result['environment_roots'][str(base)]=sorted(p.name for p in base.iterdir())[:30]
pids=[]
for line in result['compute_processes']['stdout'].splitlines():
 token=line.split(',')[0].strip()
 if token.isdigit():pids.append(token)
result['process_identity']=[]
for pid in pids:
 row={'pid':pid,'ps':run(['ps','-p',pid,'-o','pid,ppid,user,etimes,comm'])}
 for key in ['cwd','exe']:
  try:row[key]=os.readlink('/proc/'+pid+'/'+key)
  except OSError as e:row[key]=str(e)
 result['process_identity'].append(row)
print(json.dumps(result,ensure_ascii=False,indent=2))
