"""Read completed rep01 route artifacts only; never run a planner or simulator."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REMOTE = "gpu5070ti"
BASE = "/data/sun/vla_mppi_20261009"
EXPERIMENT = ".pipeline/experiments/2026-09-26_newton_stair_reproduction"

REMOTE_READER = r'''
import base64, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
base=Path('/data/sun/vla_mppi_20261009')
experiment=base/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
sha=lambda data:hashlib.sha256(data).hexdigest()
manifest=experiment/'versions/v242/cases_manifest.json'
cases=json.loads(manifest.read_text())['cases']
result={'collected_utc':datetime.now(timezone.utc).isoformat(),
        'remote_host':'gpu5070ti','base':str(base),
        'cases_manifest_sha256':sha(manifest.read_bytes()),'versions':{},'fixtures':{}}
for case in cases:
    cid=case['case_id'];root=base/'generalization_v242/cases'/cid
    result['fixtures'][cid]={'case':case,'files':{}}
    for name in ('endpoints.txt','scenario.json','fixture.json'):
        p=root/name;data=p.read_bytes()
        result['fixtures'][cid]['files'][name]={'remote_path':str(p),'sha256':sha(data),
            'bytes':len(data),'text':data.decode()}
for version,folder in [('v247','physical_traversability_v247'),('v251','generic_mechanisms_v251')]:
    root=base/folder/'evaluation/scored';rows={}
    entry={'remote_scored_root':str(root),'cases':rows,'source_binding':{}}
    for name in ('manifest.json','native_probe.cpp','run_matrix.py','results/source_inventory.json'):
        p=experiment/'versions'/version/name;data=p.read_bytes()
        entry['source_binding'][name]={'remote_path':str(p),'sha256':sha(data),'bytes':len(data)}
    progress=root.parent/'matrix_progress.json'
    if progress.exists():
        data=progress.read_bytes();entry['completed_matrix_calls']=len(json.loads(data))
        entry['progress_sha256']=sha(data)
    for case in cases:
        cid=case['case_id'];target=root/cid/'rep01';summary=target/'summary.json'
        if not summary.exists():
            rows[cid]={'completed':False};continue
        payload={};info={'completed':True,'remote_directory':str(target),'files':{}}
        parsed=json.loads(summary.read_text())
        for name in ('summary.json','route.csv'):
            p=target/name
            if not p.exists():continue
            data=p.read_bytes();h=sha(data)
            if name=='route.csv':assert h==parsed['hashes']['route.csv'],str(p)
            info['files'][name]={'remote_path':str(p),'sha256':h,'bytes':len(data),
                'base64':base64.b64encode(data).decode()}
        log=target/'stdout.log'
        if log.exists():
            data=log.read_bytes();assert sha(data)==parsed['hashes']['stdout.log']
            info['stdout_sha256']=sha(data)
            info['diagnostic_lines']=[line for line in data.decode(errors='replace').splitlines()
                if any(s in line for s in ('pct_optimizer_rejected','pct_shared_rejected','STATIC_REQUEST'))]
        rows[cid]=info
    result['versions'][version]=entry
print(json.dumps(result))
'''


def main() -> None:
    command = ["ssh", "-S", "none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
               REMOTE, "python3", "-"]
    completed = subprocess.run(command, input=REMOTE_READER, text=True, capture_output=True, check=True)
    receipt = json.loads(completed.stdout)
    for version, entry in receipt["versions"].items():
        for cid, case in entry["cases"].items():
            for name, artifact in case.get("files", {}).items():
                data = base64.b64decode(artifact.pop("base64"))
                assert hashlib.sha256(data).hexdigest() == artifact["sha256"]
                destination = HERE / "inputs" / version / cid / "rep01" / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
                artifact["local_path"] = str(destination.relative_to(HERE))
    target = HERE / "collection_receipt.json"
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    for version, entry in receipt["versions"].items():
        done = [cid for cid, c in entry["cases"].items() if c["completed"]]
        print(version, "complete rep01:", ", ".join(done),
              "matrix calls:", entry.get("completed_matrix_calls"))
    print("receipt_sha256", hashlib.sha256(target.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
