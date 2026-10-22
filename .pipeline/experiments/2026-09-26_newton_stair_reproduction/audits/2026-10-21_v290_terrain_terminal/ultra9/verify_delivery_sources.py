"""Local verification of returned code/config and remote heavy-data identities."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[6]
E=ROOT/'.pipeline/experiments/2026-09-26_newton_stair_reproduction'
H=Path(__file__).resolve().parent
V=E/'versions/v290'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    m=json.loads((H/'physical_manifest01.json').read_text())
    returned=json.loads((H/'dependency_return01/return_manifest.json').read_text())
    assert returned['physical_manifest_sha256']==sha(H/'physical_manifest01.json')
    assert returned['all_remote_files_verified']
    matched=[];remote=[]
    for rel,digest in m['files'].items():
        p=None
        if rel.startswith('repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v290/'):
            tail=rel.split('/versions/v290/',1)[1]
            if tail in ['native_manifest.json','source_inventory.json'] or tail.startswith('src/'):p=V/tail
            elif tail=='launch.py':p=H/'physical_template.py'
            else:p=H/'runtime_version'/tail
        elif rel.startswith('repo/'):p=ROOT/rel[5:]
        elif rel.startswith('migration/bin/'):p=H/'runtime_binding/bin'/rel[len('migration/bin/'):]
        elif rel.startswith('migration/'):p=H/rel[len('migration/'):]
        elif rel.startswith('source/'):p=V/rel[len('source/'):]
        elif rel.startswith('profile_reference/'):p=H/'runtime_binding/profile_reference'/rel[len('profile_reference/'):]
        elif rel.startswith('native/fixtures/'):p=H/'runtime_binding/fixtures'/rel[len('native/fixtures/'):]
        elif rel.startswith('benchmark/'):p=H/'offline'/rel[len('benchmark/'):]
        elif rel.startswith('evidence/'):p=H/'evidence'/rel[len('evidence/'):]
        if p is None or not p.is_file():p=H/'dependency_return01'/rel
        if p.is_file():
            assert sha(p)==digest,(rel,str(p))
            matched.append(rel)
        else:
            record=returned['remote_retained'][rel]
            assert record['sha256']==digest
            assert Path(rel).suffix not in ['.py','.cpp','.cc','.h','.hpp','.inc','.sh','.gdb','.xml','.yaml','.yml']
            remote.append(rel)
    native=json.loads((V/'native_manifest.json').read_text())
    for rel,digest in native['source_files'].items():assert sha(V/rel)==digest,rel
    result=dict(passed=True,physical_manifest_sha256=sha(H/'physical_manifest01.json'),
        native_manifest_sha256=sha(V/'native_manifest.json'),declared_files=len(m['files']),
        local_bytes_matches=len(matched),remote_heavy_files=len(remote),remote_heavy_keys=remote,
        all_remote_files_verified=returned['all_remote_files_verified'],native_declared_sources=len(native['source_files']),
        mismatches=0,physics_steps=0)
    (H/'evidence/execution_local_return01.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
