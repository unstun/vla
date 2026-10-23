"""Locate existing audited violations; no new probe, scoring rule or physics."""
from pathlib import Path
import csv,hashlib,json
ROOT=Path('/home/ubuntu/sun/vla_v291_pair24_20261022')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
data=json.loads((ROOT/'analysis/summary.json').read_text());assert data['full_geometry'] and len(data['runs'])==24
events=[];provenance={}
for run in data['runs']:
 out=ROOT/'analysis'/run['run'];streams={};first_zero=(run['stop'].get('first') or {}).get('start_s')
 for name in ('navigation_and_tail','factory'):
  csv_file=out/(name+'_all_margins.csv');support_file=out/(name+'_support.jsonl')
  body=list(csv.DictReader(csv_file.open()));support=[json.loads(x) for x in support_file.read_text().splitlines()];times=[float(x.split()[0]) for x in (out/(name+'_poses.txt')).read_text().splitlines()];assert len(body)==len(support)==len(times)
  samples=[]
  for index,(b,s) in enumerate(zip(body,support),1):
   t=times[index-1];assert abs(t-float(s['case_id']))<1e-6 and abs(t-float(b['time_s']))<1e-3
   margins=dict(support_gap_m=s['support_gap_extra_margin_m'],source_solid_m=float(b['native_source_solid_margin_m']),raw_point_m=float(b['raw_point_margin_m']))
   samples.append(dict(row=index,time_s=t,minimum_margin_m=min(margins.values()),margins=margins))
  bad=[x for x in samples if x['minimum_margin_m'] < -1e-10]
  streams[name]=dict(samples=len(samples),violating_samples=len(bad),first_violation=bad[0] if bad else None,worst=min(samples,key=lambda x:x['minimum_margin_m']),first_violation_minus_first_zero_s=bad[0]['time_s']-first_zero if bad and first_zero is not None else None,csv_sha256=sha(csv_file),support_sha256=sha(support_file))
 events.append(dict(run=run['run'],first_zero_s=first_zero,streams=streams))
 resource=ROOT/'evidence'/run['run']/'actual_resources.json';cfg=json.loads(resource.read_text());assert cfg['NanoCpus']==6000000000 and cfg['Memory']==6442450944
 provenance[run['run']]=dict(actual_resources=cfg,resources_sha256=sha(resource),summary_sha256=sha(out/'summary.json'),geometry_sha256=sha(out/'geometry.json'),analysis_sha256=run['analysis_sha256'])
(ROOT/'analysis/geometry_events.json').write_text(json.dumps(dict(new_physics_steps=0,runs=events),indent=2)+'\n')
(ROOT/'analysis/analysis_provenance.json').write_text(json.dumps(dict(host='ultra9',campaign_root=str(ROOT),summary_sha256=sha(ROOT/'analysis/summary.json'),geometry_events_sha256=sha(ROOT/'analysis/geometry_events.json'),geometry_events_script_sha256=sha(Path(__file__)),runs=provenance),indent=2)+'\n')
print('Located original geometry violations and verified all24 resource records.')
