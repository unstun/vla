"""Prepare the six corrected checks from the already verified first export."""
import argparse
import hashlib
import json
import os
from pathlib import Path

def prepare(source,output):
    output.mkdir(exist_ok=False)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ['a01_g01','a03_g05','a05_g01','a01_pause65','a01_pause76','a03_pause68']:
        src=source/name;dst=output/name;dst.mkdir()
        d=json.loads((src/'identity.json').read_text());attempt=name[1:3]
        for filename,digest in d['files'].items():assert sha(src/filename)==digest
        available=max((p.read_text().splitlines() for p in source.glob(f'a{attempt}_*/scans.txt')),key=len)
        if 'pause' in name:
            rows=[r for r in available if int(r.split()[1])/1e9<=d['query_s']-.15]
            observed=int(rows[-1].split()[1])/1e9
            assert 0<=d['query_s']-observed<=.25
            d['observation_s']=observed
            d['observation_selection']='Controlled fresh prefix from already returned original scans; newest source at least 150 ms before query, not original asynchronous revision.'
        else:
            rows=(src/'scans.txt').read_text().splitlines()
            d['observation_selection']='Original recorded controller proof source stamp'
        for row in rows:
            for n in row.split()[2:]:(dst/n).symlink_to(os.path.relpath(source/f'scans_{attempt}'/n,dst))
        (dst/'scans.txt').write_text('\n'.join(rows)+'\n')
        for n in ['query_body.txt','query.txt','curve.txt']:(dst/n).write_bytes((src/n).read_bytes())
        for n in ['navigation.f32','surface.f32','physical_floor.f32']:(dst/n).symlink_to(os.path.relpath(source/'static'/n,dst))
        d['scans']=len(rows);d['parent_identity_sha256']=sha(src/'identity.json')
        d['files']={p.name:sha(p) for p in dst.iterdir() if p.is_file()}
        (dst/'identity.json').write_text(json.dumps(d,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();prepare(a.source.resolve(),a.output.resolve())
