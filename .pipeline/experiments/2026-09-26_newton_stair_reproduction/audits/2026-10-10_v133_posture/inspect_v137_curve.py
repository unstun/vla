import sys,json,re,math,subprocess
from pathlib import Path
import numpy as np
from scipy.interpolate import BSpline
t=Path('/data/sun/vla_mppi_20261009');b=t/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
sys.path.insert(0,str(b/'versions/v127'))
from analyze_remote import Capture
c=Capture(t/'trials/v137_candidate_attempt03/runs/v137_candidate_attempt03');lines=c.read('nav2.log').splitlines();start=next(i for i,s in enumerate(lines) if 'V132_REFERENCE_ADMISSION generation=2' in s)
last=None
for i,l in enumerate(lines[start:],start):
 if 'spline_curve_capture ' in l:last=json.loads(l.split('spline_curve_capture ',1)[1])
 if 'final_spline_rejected' in l and last:
  tm=float(re.search(r' t=([0-9.]+)',l).group(1));curve=BSpline(last['knots'],np.array(last['controls']),3);p=curve(tm);ahead=curve(tm+.8);yaw=math.atan2(*(ahead-p)[[1,0]]);h=np.array([.18*math.cos(yaw),.18*math.sin(yaw),0])
  ps=np.array([p+h,p-h]);ps[:,2]-=.3
  out=t/'results/v133_posture/v137_curve_geometry';out.mkdir(exist_ok=False);ps.astype('<f8').tofile(out/'queries.f64')
  receipt=json.loads((t/'support_coverage_v134/receipt.json').read_text())
  subprocess.run([str(t/'global_coverage_v135_foxy/query_mask'),str(t/'support_coverage_v134/partial.txt'),receipt['fnv64'],'.35',str(out/'queries.f64'),str(out/'blocked.u8')],check=True)
  r={'time':tm,'position':p.tolist(),'ahead':ahead.tolist(),'yaw':yaw,'cylinders_ground':ps.tolist(),'gap_veto':np.fromfile(out/'blocked.u8',dtype=np.uint8).tolist(),'curve':last,'rejection':l,'capture_sources':c.sources}
  (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['curve','capture_sources']}));break
