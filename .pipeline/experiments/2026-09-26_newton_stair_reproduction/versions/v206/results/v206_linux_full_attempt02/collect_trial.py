"""Validate the closed remote recording; return compact provenance only."""
from pathlib import Path
import hashlib,json,math,sys,zipfile
H=Path(__file__).resolve().parent;V=H.parents[2];T=Path('/data/sun/vla_mppi_20261009')
R=T/'trials/v206_linux_full_attempt02/runs/v206_linux_full_attempt02'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
process=json.loads((R/'process.json').read_text());assert process['exit_code']==0 and not process['timed_out']
retention=json.loads((R/'retention_result.json').read_text());assert retention['status']=='completed'
m=json.loads((R/'raw_capture_manifest.json').read_text());assert sha(R/'raw_capture.zip')==m['archive_sha256']
with zipfile.ZipFile(R/'raw_capture.zip') as z:
 for name,e in m['members'].items():
  data=z.read(name);assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256'],name
 log=z.read('nav2.log').decode(errors='replace')
 failure=[line for line in log.splitlines() if '[controller_server]' in line and 'terminal_settle_timeout' in line]
 assert len(failure)==1,failure
 telemetry=[json.loads(line) for line in z.read('telemetry.jsonl').decode().splitlines() if line.strip()]
last=telemetry[-1]
frames=json.loads((R/'video_states.json').read_text());final=frames[-1]
original=json.loads((V.parent/'inputs/historical_full_building.json').read_text())
goal=original['goal_ground_xyz_m'];xyz=final['joint_q'][:3]
from launch import verify_sources
identity=verify_sources()
record={'run':R.name,'host':'gpu5070ti','physical_integration':'v206','closed':True,
 'raw_root':str(R),'raw_archive':str(R/'raw_capture.zip'),'archive_bytes':(R/'raw_capture.zip').stat().st_size,
 'archive_sha256':m['archive_sha256'],'archive_members_verified':len(m['members']),
 'process_exit_code':process['exit_code'],'navigation_status':'FAILED','failure':'terminal_settle_timeout',
 'failure_log':failure[0],'full_route_gate_passed':False,'final_stance_mode':final['stance_mode'],
 'final_policy_owns_joints':final['policy_owns_joints'],'final_command':final['command'],
 'final_body_xyz_m':xyz,'final_goal_xy_error_m':math.dist(xyz[:2],goal[:2]),
 'final_height_error_m':abs(xyz[2]-goal[2]-original['locomotion_reference_height_m']),
 'physics_duration_s':final['physics_time_s'],'source_identity_after':identity,
 'retrieve_raw':'rsync -az gpu5070ti:'+str(R/'raw_capture.zip')+' DESTINATION/',
 'reanalyze':'/home/sun/vla_exec/envs/newton_worker/bin/python '+str(H/'analyze.py')}
(H/'remote_artifacts.json').write_text(json.dumps(record,indent=2)+'\n')
(H/'terminal_telemetry.json').write_text(json.dumps(last,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ['run','navigation_status','failure','final_stance_mode','final_goal_xy_error_m','physics_duration_s','archive_members_verified']}))
