"""Capture read-only runtime identity without root or a robot command socket."""

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent
remote = r'''import datetime,hashlib,json,pathlib,platform,subprocess
root=pathlib.Path('/home/ysc/jy_exe')
pids=subprocess.run(['pgrep','-x','jy_exe'],capture_output=True,text=True).stdout.split()
processes=[]
for pid in pids:
    path=pathlib.Path('/proc')/pid
    entry={'pid':int(pid),'argv0':(path/'cmdline').read_bytes().split(b'\0')[0].decode(errors='replace')}
    entry['status']=[line for line in (path/'status').read_text().splitlines() if line.startswith(('Name:','Uid:','Threads:'))]
    entry['ps']=subprocess.run(['ps','-p',pid,'-o','pid=,comm=,lstart=,etime='],capture_output=True,text=True).stdout.strip()
    processes.append(entry)
files=[]
for rel in ['bin/jy_exe','lib/ras_lib/libdeepras.so','scripts/run.sh','conf/name.toml','conf/motor.toml','conf/Algorithm.toml','conf/model_config.yaml']:
    path=root/rel
    files.append({'path':str(path),'relative_path':rel,'resolved_path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
service=subprocess.run(['systemctl','show','jy_exe','--property=MainPID,ExecStart,WorkingDirectory,FragmentPath,ActiveState'],capture_output=True,text=True).stdout
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.uname()._asdict(),'os_release':pathlib.Path('/etc/os-release').read_text(),'processes':processes,'files':files,'service':service},indent=2))
'''
command = [
    "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
    "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=5",
    "-o", "ServerAliveCountMax=2", "ysc@192.168.2.1", "python3 -",
]
reply = subprocess.run(command, input=remote, text=True, capture_output=True,
                       check=True, timeout=20)
evidence = json.loads(reply.stdout)
manifest = json.loads((ROOT / "source_manifest.json").read_text())
expected = {item["relative_path"]: item["sha256"] for item in manifest["files"]}
evidence["snapshot_hashes_still_match"] = all(
    item["sha256"] == expected[item["relative_path"]] for item in evidence["files"]
)
(ROOT / "remote_after_inspection.json").write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps({"processes": evidence["processes"],
                  "snapshot_hashes_still_match": evidence["snapshot_hashes_still_match"]}, indent=2))
