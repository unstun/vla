"""Verify execution inputs against the local source and selected dependencies."""
import argparse
import hashlib
import json
from pathlib import Path

EXP=Path(__file__).resolve().parents[1]

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--create',action='store_true');args=parser.parse_args()
    path=EXP/'setup/source_manifest.json'
    if args.create:
        upstream=EXP.parents[2]/'references/upstream/2026-09-10_navdp_lite3/source'
        sources={}
        for part in ['scripts','lib','assets','policy','cases']:
            for f in (EXP/part).rglob('*'):
                if f.is_file() and '__pycache__' not in f.parts and not f.name.startswith('._'):
                    sources[str(f.relative_to(EXP))]=digest(f)
        for folder,prefix in [(upstream/'NavDP/baselines/x-navdp','work/x-navdp'),(upstream/'acados','work/acados')]:
            for f in folder.rglob('*'):
                if f.is_file() and '.git' not in f.parts and not f.name.startswith('._'):
                    sources[prefix+'/'+str(f.relative_to(folder))]=digest(f)
        sources['tools/t_renderer']=digest(EXP/'tools/t_renderer')
        override='work/x-navdp/src/utils/mpc_tracking.py'
        if (EXP/override).is_file():sources[override]=digest(EXP/override)
        for name in ['selected_model.json','runtime_requirements.txt','dependency_provenance.json']:
            sources['setup/'+name]=digest(EXP/'setup'/name)
        selected=json.loads((EXP/'setup/selected_model.json').read_text())
        sources['models/'+selected['file']]=selected['sha256']
        path.write_text(json.dumps(sources,indent=2)+'\n');print('created',len(sources))
    else:
        sources=json.loads(path.read_text());failures=[]
        for name,sha in sources.items():
            f=EXP/name
            if not f.is_file() or digest(f)!=sha:failures.append(name)
        result={'checked':len(sources),'failures':failures}
        (EXP/'setup/source_verification.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
        if failures:raise RuntimeError('Execution source mismatch')

if __name__=='__main__':main()
