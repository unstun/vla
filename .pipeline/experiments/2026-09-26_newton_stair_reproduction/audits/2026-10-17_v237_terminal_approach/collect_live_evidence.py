"""Compact live-clock native receipts, with explicit fixed-motion boundary."""
from pathlib import Path
import csv
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
WORK=Path('/data/sun/vla_mppi_20261009/terminal_approach_v238')
OUT=HERE/'results/live_clock';OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary={}
for name in ('baseline_window01','candidate_window01','candidate_window02'):
    folder=WORK/name;target=OUT/name;target.mkdir(exist_ok=True)
    result=json.loads((folder/'live_window.json').read_text())
    for file in ('live_window.json','live_events.csv','emergency_context.csv'):
        if (folder/file).is_file():shutil.copy2(folder/file,target/file)
    rows=list(csv.DictReader((folder/'live_events.csv').open()))
    result['emergency_times_s']=[float(r['ros_s']) for r in rows if r['kind']=='spline' and r['success_or_emergency']=='1']
    log=WORK/(name+'.log');lines=log.read_text().splitlines();keep=set()
    for i,line in enumerate(lines):
        if '[SAFETY]' in line or '[BODY_TIME_INPUT]' in line:
            keep.update(range(max(0,i-30),min(len(lines),i+8)))
    (target/'failure_context.log').write_text('\n'.join(f'{i+1}: '+lines[i][:1600]+(' [compact truncation]' if len(lines[i])>1600 else '') for i in sorted(keep))+'\n')
    result['full_log']=dict(path=str(log),sha256=sha(log),bytes=log.stat().st_size)
    summary[name]=result
assert summary['baseline_window01']['initial_digest']==summary['candidate_window01']['initial_digest']==summary['candidate_window02']['initial_digest']
assert len({(r['body_messages'],r['sensor_poses'],r['clouds']) for r in summary.values()})==1
summary['scope']='Real wall/ROS clock, 2-thread native executor with original mutually exclusive callbacks, original DDS due-message stream, native asynchronous mapper handoff, initial state restored once. Body follows the old physical recording, not newly generated commands. Initial mapping-window scheduling history is not exactly restored.'
summary['input_identity']=dict(path=str(WORK/'input04'),stream_sha256=sha(WORK/'input04/stream.txt'),frames_sha256=sha(WORK/'input04/frames.txt'))
summary['probe_source_sha256']=sha(HERE/'replay_probe.cpp')
summary['zero_emergency_gate_passed']=all(summary[name]['emergency_messages']==0 for name in ('candidate_window01','candidate_window02'))
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
shutil.copy2(HERE/'replay_probe.cpp',OUT/'executed_probe.cpp')
shutil.copy2(HERE/'replay.sh',OUT/'executed_replay.sh')
print(json.dumps({name:summary[name] for name in ('baseline_window01','candidate_window01','candidate_window02')},indent=2))
