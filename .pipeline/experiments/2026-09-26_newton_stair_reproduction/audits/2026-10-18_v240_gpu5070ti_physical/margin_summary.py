"""Compare actual body yaw/height under one fixed native environmental field."""
from pathlib import Path
import csv,json
import numpy as np
HERE=Path(__file__).resolve().parent;OUT=HERE/'results'
report={}
comparison=json.loads((OUT/'comparison.json').read_text())
for version in ('v241',):
 path=HERE/'work'/(version+'_linux_full_attempt01_margins.csv')
 rows=list(csv.DictReader(path.open()))
 def summarize(part):
  known=[float(r['extra_edge_margin_m']) for r in part if int(r['floor_known'])]
  return {'samples':len(part),'floor_known_samples':len(known),'floor_unknown_fraction':1-len(known)/len(part) if part else None,
   'minimum_extra_edge_margin_m':min(known) if known else None,'p05_extra_edge_margin_m':float(np.quantile(known,.05)) if known else None,
   'negative_margin_fraction_of_known':sum(x<0 for x in known)/len(known) if known else None,
   'at_target_fraction_of_known':sum(x>=.15-1e-10 for x in known)/len(known) if known else None}
 window=[r for r in rows if 45<=float(r['time_s'])<55]
 region=[r for r in rows if 6.7<=float(r['x'])<=8.8 and -4.8<=float(r['y'])<=-2.8 and 1.3<=float(r['z'])<=2.3]
 report[version]={'window_45_55':summarize(window),'window_109_115':summarize([r for r in rows if 109<=float(r['time_s'])<115]),'same_spatial_stair_region':summarize(region),'whole_recording':summarize(rows)}
 failure=comparison[version]['window_45_55'].get('last_reactive_collision_ros_s') if comparison[version]['window_45_55']['controller_crash_lines'] else None
 if version=='v231' and failure is not None:
  # Exclude a conservative uncertainty interval around the approximately observed abort.
  report[version]['controller_failure_split']={'before_s':failure,'after_s':47.0,'excluded_uncertain_interval_s':[failure,47.0],
   'window_active_prefix':summarize([r for r in window if float(r['time_s'])<failure]),
   'window_after_failure':summarize([r for r in window if float(r['time_s'])>=47]),
   'spatial_region_active_prefix':summarize([r for r in region if float(r['time_s'])<failure]),
   'spatial_region_after_failure':summarize([r for r in region if float(r['time_s'])>=47])}
baseline=HERE.parent/'2026-10-17_v237_gpu5070ti_physical/results/body_edge_margin_comparison.json'
report['v237']=json.loads(baseline.read_text())['v237']
report['definition']={'source':'actual sensor body XYZ and quaternion (wxyz), actual planar yaw; no zero-yaw substitution',
 'field':'same frozen ENV225 bytes/FNV 10040917858432847476 for this new run; radius .35, offset .18',
 'metric':'extra support-edge margin, capped at the .15m target; negative means deficit relative to .35m envelope',
 'scope':'offline body geometry only; floor association is not selectedSurface admission or leg-contact evidence. Whole recording/spatial totals include post-crash standing; use active-prefix split for route behavior.'}
(OUT/'body_edge_margin_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
