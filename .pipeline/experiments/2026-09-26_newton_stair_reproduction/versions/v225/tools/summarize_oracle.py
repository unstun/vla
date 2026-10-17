"""Report approximation errors separately from independent gradient checks."""
from pathlib import Path
import json
import numpy as np

work=Path('/data/sun/vla_mppi_20261009/environment_lookup_v225')
a=np.genfromtxt(work/'oracle01.csv',delimiter=',',names=True)
def stats(mask):
    rows=a[mask];result={'samples':len(rows)}
    if not len(rows):return result
    for label,error in [('edge_abs',abs(rows['new_edge']-rows['old_edge'])),
                        ('solid_abs',abs(rows['new_solid']-rows['old_solid'])),
                        ('solid_optimism',np.maximum(rows['new_solid']-rows['old_solid'],0)),
                        ('cost_abs',abs(rows['new_cost']-rows['old_cost']))]:
        result[label]={'mean':float(error.mean()),'p95':float(np.quantile(error,.95)),
                       'p99':float(np.quantile(error,.99)),'max':float(error.max())}
    return result
report={'samples':len(a),'all':stats(np.ones(len(a),dtype=bool)),
        'known_nonswitch':stats((a['floor_known']==1)&(a['switch_band']==0)),
        'known_switch_band':stats((a['floor_known']==1)&(a['switch_band']==1)),
        'unknown_floor':stats(a['floor_known']==0),
        'groups':{str(i):stats(a['group']==i) for i in range(7)},
        'gradient':{'smooth_axes':int(a['smooth_axes'].sum()),'nonsmooth_axes_reported':int(a['nonsmooth_axes'].sum()),
                    'maximum_relative_error':float(a['gradient_error'].max()),
                    'rows_over_1e_3':int((a['gradient_error']>1e-3).sum())},'physics_steps':0}
(work/'oracle_summary01.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'samples':len(a),'known_nonswitch':report['known_nonswitch'],
                 'known_switch_band':report['known_switch_band'],'gradient':report['gradient']}))
assert report['gradient']['rows_over_1e_3']==0
assert report['all']['edge_abs']['max']<1e-8
