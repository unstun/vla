#!/usr/bin/env python3
"""Trace native fatal signals and preserve their child exit semantics."""
from pathlib import Path
import json,os,signal,subprocess,sys
root=Path(os.environ['V289_BACKTRACE_DIR']);root.mkdir(parents=True,exist_ok=True)
name=Path(sys.argv[1]).name+'-'+str(os.getpid())
status=root/(name+'.json');log=root/(name+'.log')
environment=dict(os.environ,V289_DEBUG_STATUS=str(status),V289_DEBUG_LOG=str(log))
# ROS launch delivers shutdown signals to this whole process group.
for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:None)
code=subprocess.call(['/usr/bin/gdb','--batch','--quiet','--nx','-x',str(Path(__file__).with_name('native_backtrace.gdb')),'--args']+sys.argv[1:],env=environment)
if status.exists():
    state=json.loads(status.read_text())
    if state['signal']:
        sig=getattr(signal,state['signal']);signal.signal(sig,signal.SIG_DFL);os.kill(os.getpid(),sig)
raise SystemExit(code)
