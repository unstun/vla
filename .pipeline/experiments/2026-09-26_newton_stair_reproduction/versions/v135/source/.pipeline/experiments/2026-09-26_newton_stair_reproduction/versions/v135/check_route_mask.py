from pathlib import Path
import json, numpy as np,subprocess,math,hashlib
t=Path('/data/sun/vla_mppi_20261009');o=t/'global_coverage_v135_foxy';out=t/'results/v135_routecheck';out.mkdir(exist_ok=False)
r=json.loads((o/'pct_result.json').read_text());c=json.loads((t/'support_coverage_v134/receipt.json').read_text());rows=[]
for v in r['cases']:
 p=np.asarray(v['points']);xs=[]
 for a,b in zip(p,p[1:]):
  n=max(2,int(np.linalg.norm(b-a)/.025)+1);yaw=math.atan2(b[1]-a[1],b[0]-a[0]);h=np.array([.18*math.cos(yaw),.18*math.sin(yaw),0])
  for x in np.linspace(a,b,n):
   x=x.copy();x[2]-=.3;xs.extend([x+h,x-h])
 np.asarray(xs,dtype='<f8').tofile(out/(v['variant']+'.f64'))
 subprocess.run([str(o/'query_mask'),str(t/'support_coverage_v134/partial.txt'),c['fnv64'],'.35',str(out/(v['variant']+'.f64')),str(out/(v['variant']+'.u8'))],check=True)
 bad=np.fromfile(out/(v['variant']+'.u8'),dtype=np.uint8)
 row={'variant':v['variant'],'start':p[0].tolist(),'end':p[-1].tolist(),'length':float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()),'blocked':int(bad.sum()),'queries':len(bad),'first_bad':np.asarray(xs)[bad.astype(bool)][:3].tolist()};rows.append(row)
 print(json.dumps(row))
(out/'result.json').write_text(json.dumps(rows,indent=2)+'\n')

