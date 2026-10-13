"""Verify inspected pinned primary source files against their canonical URLs."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[5]
SOURCE=ROOT/'references/upstream/2026-10-09_navigation_qualification/source'
REPOS=['ros-navigation__navigation2','ros-planning__navigation','wuyi2121__SCAN-Planner',
       'rst-tu-dortmund__teb_local_planner','jizhang-cmu__autonomy_stack_go2',
       'ZJU-FAST-Lab__ego-planner','HKUST-Aerial-Robotics__Fast-Planner','mit-acl__faster',
       'leggedrobotics__art_planner','ori-drs__field_local_planner']


def verify(item):
    path=ROOT/item['local_path'];data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==item['sha256'],str(path)
    try:
        request=urllib.request.Request(item['url'],headers={'User-Agent':'vla-stop-cause-source-audit'})
        with urllib.request.urlopen(request,timeout=25) as f:raw=f.read()
        return dict(item,local_match=True,remote_match=hashlib.sha256(raw).hexdigest()==item['sha256'],bytes=len(raw))
    except Exception as e:return dict(item,local_match=True,remote_match=None,error=str(e))


def main():
    items=[];repos=[]
    for name in REPOS:
        directory=SOURCE/name;m=json.loads((directory/'metadata.json').read_text())
        repos.append({k:m.get(k) for k in ('canonical_repository','pinned_commit','default_branch','license_api','archived','pushed_at')})
        for f in m['files']:
            if f['path'].endswith(('.cpp','.cc','.py')) or f['path']=='LICENSE':
                items.append(dict(f,repository=m['canonical_repository'],commit=m['pinned_commit'],local_path=str((directory/f['path']).relative_to(ROOT))))
    directory=ROOT/'references/upstream/2026-10-08_nav2_foxy_plugin'
    m=json.loads((directory/'provenance.json').read_text())
    for f in m['files']:
        if f['path'].endswith('.cpp'):
            items.append(dict(f,repository='ros-navigation/navigation2',commit=m['commit'],local_path=str((directory/f['path']).relative_to(ROOT))))
    with ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(verify,items))
    out=Path(__file__).resolve().parent/'upstream_verification.json'
    out.write_text(json.dumps({'repositories':repos,'files':files,'status':'surveyed','upstream_runtime_executed':False},indent=2)+'\n')
    print(json.dumps({'repositories':len(repos),'files':len(files),'remote_matches':sum(x['remote_match'] is True for x in files),'unavailable':[x['url'] for x in files if x['remote_match'] is None]}))

if __name__=='__main__':main()
