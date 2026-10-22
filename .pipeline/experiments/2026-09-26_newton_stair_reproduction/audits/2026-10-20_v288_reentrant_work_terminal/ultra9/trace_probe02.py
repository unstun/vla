from pathlib import Path
import json,subprocess,os,signal
R=Path('/home/ubuntu/sun/vla_v288_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288';D=R/'trace_probe02';D.mkdir()
image=json.loads((R/'evidence/debug_image01.json').read_text())['image']
common=['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}','--cpus=2','--memory=6g','-e','V288_BACKTRACE_DIR=/evaluation/stacks','-v',str(D)+':/evaluation:rw','-v',str(V)+':/source:ro','-v',str(R/'migration')+':/helpers:ro','--entrypoint','/bin/bash',image,'-c']
subprocess.run(common+['c++ -std=c++17 -O0 -g -fno-omit-frame-pointer /helpers/trace_probe.cpp -pthread -o /evaluation/trace_child'],check=True)
checks=[]
for sig in [signal.SIGSEGV,signal.SIGBUS,signal.SIGABRT,signal.SIGILL,signal.SIGFPE]:
 with (D/(sig.name+'.log')).open('x') as f:
  code=subprocess.run(common+['python3 /source/native_debugger.py /evaluation/trace_child '+str(sig.value)],stdout=f,stderr=subprocess.STDOUT).returncode
 states=[json.loads(p.read_text()) for p in (D/'stacks').glob('*.json')]
 logs=[p.read_text() for p in (D/'stacks').glob('*.log') if 'V288_NATIVE_SIGNAL '+sig.name in p.read_text()]
 passed=code==128+sig.value and any(s['signal']==sig.name for s in states) and len(logs)==1 and all(name in logs[0] for name in ['fault_level_three','fault_level_two','fault_level_one','Thread 2'])
 checks.append(dict(signal=sig.name,container_returncode=code,passed=passed))
 print(checks[-1],flush=True)
result=dict(passed=all(c['passed'] for c in checks),physics_steps=0,debug_image=image,checks=checks)
(R/'evidence/trace_probe02.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed']
