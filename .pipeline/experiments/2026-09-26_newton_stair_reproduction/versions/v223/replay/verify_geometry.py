"""Independent FCL oracle over the exact C++ OBB/voxel predicate used in replay."""
from pathlib import Path
import hashlib,json,os,subprocess
import numpy as np
import fcl
ROOT=Path('/data/sun/vla_mppi_20261009');WORK=ROOT/'floor_reason_v223';SOURCE=ROOT/'source_v223'
source=(SOURCE/'replay/collision_probe.cpp').read_text()
section=source[source.index('struct TorsoBox'):source.index('Causes occupancyCauses')]
cpp='#include <Eigen/Dense>\n#include <vector>\n#include <iostream>\n#include <cmath>\n'+section+'''\nint main(){Eigen::Vector3d voxel,body;TorsoBox box;double yaw,half;while(std::cin>>body.x()>>body.y()>>body.z()>>voxel.x()>>voxel.y()>>voxel.z()>>yaw>>box.center.x()>>box.center.y()>>box.center.z()>>box.half.x()>>box.half.y()>>box.half.z()>>half){const Eigen::Matrix3d r=Eigen::AngleAxisd(yaw,Eigen::Vector3d::UnitZ()).toRotationMatrix();std::cout<<boxOverlap(voxel,half,body,r,box)<<"\\n";}}\n'''
(WORK/'verify_boxes.cpp').write_text(cpp)
subprocess.run(['docker','run','--rm','--network=none','--user',f'{os.getuid()}:{os.getgid()}','-v',str(WORK)+':/work:rw','--entrypoint','/usr/bin/g++','5a41a25fb20b','-std=c++17','-O2','-I/usr/include/eigen3','/work/verify_boxes.cpp','-o','/work/verify_boxes'],check=True)
rng=np.random.default_rng(223);cases=[];expected=[]
for i in range(5000):
    body=rng.uniform(-10,10,3);yaw=rng.uniform(-np.pi,np.pi);center=rng.uniform(-.1,.1,3)
    half=rng.uniform(.02,.4,3);voxel_half=rng.uniform(.005,.08)
    voxel=body+rng.uniform(-.6,.6,3)
    rotation=np.array([[np.cos(yaw),-np.sin(yaw),0],[np.sin(yaw),np.cos(yaw),0],[0,0,1]])
    if i<100:
        yaw=0.;rotation=np.eye(3);voxel=body+center+np.array([half[0]+voxel_half+(1e-7 if i%2 else -1e-7),0,0])
    torso=fcl.CollisionObject(fcl.Box(*(2*half)),fcl.Transform(rotation,body+rotation@center))
    cell=fcl.CollisionObject(fcl.Box(*([2*voxel_half]*3)),fcl.Transform(voxel))
    expected.append(bool(fcl.collide(torso,cell,fcl.CollisionRequest(),fcl.CollisionResult())))
    cases.append([*body,*voxel,yaw,*center,*half,voxel_half])
text=''.join(' '.join(format(x,'.17g') for x in row)+'\n' for row in cases)
actual=subprocess.check_output([str(WORK/'verify_boxes')],input=text,text=True)
predicted=[bool(int(x)) for x in actual.split()];assert len(predicted)==len(expected)
mismatches=[i for i,(a,b) in enumerate(zip(predicted,expected)) if a!=b]
result={'oracle':'python-fcl 0.7.0.8','samples':len(cases),'near_contact_cases':100,'mismatches':mismatches,'seed':223,'predicate_sha256':hashlib.sha256(section.encode()).hexdigest(),'cases_sha256':hashlib.sha256(text.encode()).hexdigest(),'physics_steps':0}
(WORK/'geometry_oracle.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not mismatches
