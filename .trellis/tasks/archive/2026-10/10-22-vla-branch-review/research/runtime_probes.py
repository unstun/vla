"""Read-only review of a supplied Trellis checkout using disposable Git fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--only', action='append', default=[])
args = parser.parse_args()
source = args.source.resolve()
results = []

def probe(name, fn):
    try:
        detail = fn()
        results.append({'name': name, 'status': 'pass', 'detail': detail})
    except Exception as e:
        results.append({'name': name, 'status': 'fail', 'detail': str(e)})
    print(results[-1]['status'].upper(), name, results[-1]['detail'])

class Fixture:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='vla trellis review ')
        self.root = Path(self.tmp.name)
        shutil.copytree(source/'.trellis/scripts', self.root/'.trellis/scripts', ignore=shutil.ignore_patterns('__pycache__'))
        for name in ['config.yaml','workflow.md']:
            shutil.copy2(source/'.trellis'/name, self.root/'.trellis'/name)

        for platform in ['.codex','.claude','.cursor']: (self.root/platform).mkdir()
        (self.root/'.trellis/spec').mkdir()
        (self.root/'.trellis/spec/review.md').write_text('# Test spec\n')
        self.env = dict(os.environ, TRELLIS_CONTEXT_ID='review-fixture', PYTHONDONTWRITEBYTECODE='1', GIT_AUTHOR_NAME='Review Fixture', GIT_AUTHOR_EMAIL='review@example.invalid', GIT_COMMITTER_NAME='Review Fixture', GIT_COMMITTER_EMAIL='review@example.invalid')
        for k in ['GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','TRELLIS_DEVELOPER']: self.env.pop(k,None)
        self.git('init','-q','-b','main')
        self.run('init_developer.py','review', ok=True)
        self.git('add','--','.trellis')
        self.git('commit','-q','-m','Fixture baseline')
        self.git('switch','-q','-c','review-task')
    def close(self): self.tmp.cleanup()
    def git(self,*a):
        return subprocess.run(['git',*a],cwd=self.root,env=self.env,capture_output=True,text=True,check=True).stdout.strip()
    def run(self,script,*a,ok=False):
        r=subprocess.run([sys.executable,str(self.root/'.trellis/scripts'/script),*map(str,a)],cwd=self.root,env=self.env,capture_output=True,text=True)
        if ok: assert r.returncode==0,r.stdout+r.stderr
        return r
    def create(self,slug='sample'):
        r=self.run('task.py','create','Review fixture','--description','Bounded fixture','--slug',slug,'--base-branch','main','--no-start',ok=True)
        p=self.root/r.stdout.strip().splitlines()[-1]
        assert p.is_dir(),r.stdout
        (p/'prd.md').write_text('# Goal\nVerify the fixture.\n\n## Acceptance\n- Complete the bounded check.\n')
        return p
    def curate(self,p):
        for role in ['implement','check']:
            self.run('task.py','add-context',p,role,'.trellis/spec/review.md','Fixture context',ok=True)

def using(fn):
    f=Fixture()
    try: return fn(f)
    finally: f.close()

def rejects_blank(f):
    r=f.run('task.py','create','Review fixture','--slug','missing-desc')
    assert r.returncode!=0
    assert not list((f.root/'.trellis/tasks').glob('*missing-desc')) if (f.root/'.trellis/tasks').exists() else True
    return 'Missing description rejected without a task directory.'

def context_flow(f):
    p=f.create(); f.curate(p)
    f.run('task.py','validate',p,ok=True)
    f.run('task.py','start',p,ok=True)
    assert json.loads((p/'task.json').read_text())['status']=='in_progress'
    assert p.name in f.run('task.py','current',ok=True).stdout
    f.run('task.py','finish',ok=True)
    return 'Curate, validate, activate and finish succeed.'

def inline_empty(f):
    p=f.create()
    assert (p/'implement.jsonl').exists(), 'Fixture did not seed manifests'
    r=f.run('task.py','start',p)
    assert r.returncode==0, 'dispatch_mode:inline still rejects empty manifests: '+(r.stdout+r.stderr).strip()
    return 'Inline start follows the documented exemption.'

def codex_only(f):
    (f.root/'.claude').rmdir(); (f.root/'.cursor').rmdir()
    p=f.create();f.run('task.py','start',p,ok=True)
    return 'Codex-only inline fixture starts without JSONL manifests.'

def explicit_empty(f):
    p=f.create();f.run('task.py','start',p,'--allow-empty-context',ok=True)
    return 'Documented explicit empty-context override works.'

def invalid_context(f):
    p=f.create(); f.curate(p)
    (p/'implement.jsonl').write_text('{"file": 1}\n')
    r=f.run('task.py','validate',p)
    assert r.returncode!=0 and 'Traceback' not in r.stdout+r.stderr
    return 'Invalid manifest is a validation error, not a traceback.'

def malformed_task(f):
    p=f.create(); f.curate(p); (p/'task.json').write_text('{broken')
    before=(p/'task.json').read_bytes()
    r=f.run('task.py','archive',p,'--no-commit','--skip-branch-validation')
    archived=f.root/'.trellis/tasks/archive'/datetime.now().strftime('%Y-%m')/p.name
    assert r.returncode==0 and not p.exists() and (archived/'task.json').read_bytes()==before, r.stdout+r.stderr
    assert 'archiving without updating status/children' in r.stderr
    return 'Malformed task archival warns explicitly and preserves the original bytes.'

def collision(f):
    p=f.create(); f.curate(p); f.run('task.py','start',p,ok=True)
    dest=f.root/'.trellis/tasks/archive'/datetime.now().strftime('%Y-%m')/p.name
    dest.mkdir(parents=True); (dest/'sentinel').write_text('existing archive')
    before=(p/'task.json').read_bytes();r=f.run('task.py','archive',p,'--no-commit')
    assert r.returncode!=0 and p.exists() and (p/'task.json').read_bytes()==before
    assert (dest/'sentinel').read_text()=='existing archive'
    return 'Archive collision leaves source state and destination intact.'

def archive(f):
    p=f.create(); f.curate(p); f.run('task.py','start',p,ok=True)
    head=f.git('rev-parse','HEAD'); f.run('task.py','archive',p,ok=True)
    assert not p.exists() and f.git('rev-parse','HEAD')==head
    assert not f.git('diff','--cached','--name-only')
    return 'Archive honors session_auto_commit:false; no index/commit mutation.'

def rename(f):
    parent=f.create('parent');child=f.create('child')
    f.run('task.py','add-subtask',parent,child,ok=True)
    f.curate(child);f.run('task.py','start',child,ok=True)
    f.run('task.py','rename',child,'renamed',ok=True)
    new=child.parent/(child.name[:6]+'renamed')
    assert new.exists() and not child.exists()
    assert new.name in json.loads((parent/'task.json').read_text())['children']
    assert new.name in f.run('task.py','current',ok=True).stdout
    return 'Rename updates parent link and active-session reference.'

def journal_retry(f):
    commit=f.git('rev-parse','HEAD');a=['--title','Review journal','--commit',commit,'--summary','One fixture record','--idempotency-key','review-journal']
    f.run('add_session.py',*a,ok=True)
    folder=f.root/'.trellis/workspace/review'
    before={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}
    f.run('add_session.py',*a,ok=True)
    after={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}
    assert before==after
    assert f.git('rev-parse','HEAD')==commit and not f.git('diff','--cached','--name-only')
    f.git('add','--','.trellis/workspace/review');f.git('commit','-q','-m','Record fixture')
    saved=f.git('rev-parse','HEAD');f.run('add_session.py',*a,ok=True)
    assert f.git('rev-parse','HEAD')==saved
    assert {p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}==before
    return 'Identical retry does not duplicate a pending or committed keyed journal.'

def bad_commit(f):
    folder=f.root/'.trellis/workspace/review';before={p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}
    r=f.run('add_session.py','--title','Invalid','--commit','abcdef0123456789','--summary','invalid commit')
    assert r.returncode!=0
    assert {p.name:p.read_bytes() for p in folder.iterdir() if p.is_file()}==before
    return 'Invalid commit evidence is rejected before journal writes.'

for name, fn in [('create_requires_description',rejects_blank),('task_context_lifecycle',context_flow),('inline_empty_manifest_contract',inline_empty),('codex_only_inline',codex_only),('explicit_empty_override',explicit_empty),('invalid_manifest_handling',invalid_context),('malformed_task_archive',malformed_task),('archive_collision',collision),('archive_no_auto_commit',archive),('rename_references',rename),('journal_idempotency',journal_retry),('invalid_journal_commit',bad_commit)]:
    if args.only and name not in args.only: continue
    probe(name,lambda fn=fn:using(fn))
args.output.write_text(json.dumps({'source':str(source),'probes':results,'passed':sum(r['status']=='pass' for r in results),'failed':sum(r['status']=='fail' for r in results)},indent=2)+'\n')
