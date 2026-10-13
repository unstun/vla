"""Exercise the real offline sampler with controlled geometric support cases."""
from pathlib import Path
import json,subprocess,tempfile
import numpy as np
TASK=Path('/data/sun/vla_mppi_20261009')
def plane(x0,x1,z):
    a=[x0,-.1,z];b=[x1,-.1,z];c=[x1,.1,z];d=[x0,.1,z]
    return [[a,b,c],[a,c,d]]
def main():
    results=[]
    with tempfile.TemporaryDirectory(dir=TASK/'support_coverage_v134') as tmp:
        p=Path(tmp);np.array([[0,0,.03,0]],dtype='<f4').tofile(p/'floor')
        sides=plane(-.1,-.035,0)+plane(.035,.1,0)
        for name,triangles,partial in [('solid',plane(-.1,.1,0),0),('seven_cm_gap',sides,1),
                ('permitted_step',sides+plane(-.035,.035,-.2),0),
                ('excessive_drop',sides+plane(-.035,.035,-.4),1)]:
            np.array(triangles,dtype='<f8').tofile(p/'triangles')
            got=json.loads(subprocess.check_output([str(TASK/'support_coverage_v134/generate'),str(p/'triangles'),str(p/'floor'),str(p/'partial')],text=True))
            assert got=={'cells':1,'partial':partial},(name,got)
            results.append({'case':name,'passed':True,'observed':got})
    out=TASK/'support_coverage_v134/generator_tests.json';assert not out.exists()
    out.write_text(json.dumps({'passed':True,'cases':results},indent=2)+'\n');print(out.read_text())
if __name__=='__main__':main()
