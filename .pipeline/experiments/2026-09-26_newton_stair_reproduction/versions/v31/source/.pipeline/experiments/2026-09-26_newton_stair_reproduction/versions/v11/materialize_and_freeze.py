"""Freeze native failure publication and its actual local ROS receiver."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json, shutil

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
PARENT=BASE/'runtime/scan48_ground_evidence_v10'
TARGET=BASE/'runtime/scan49_failure_notice_v11'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Pinned anchor mismatch: '+old)
    return text.replace(old,new)

def main():
    parent=json.loads((HERE.parent/'v10/manifest.json').read_text())
    if TARGET.exists() or (HERE/'manifest.json').exists():raise FileExistsError('v11 already exists')
    for name,digest in parent['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Parent source changed: '+name)
    for manifest in ['source_sha256.json','install_sha256.json']:
        for name,digest in json.loads((PARENT/manifest).read_text()).items():
            if sha(PARENT/name)!=digest:raise ValueError('Native parent changed: '+name)
    TARGET.mkdir();shutil.copytree(PARENT/'src',TARGET/'src')
    fsm=Path('src/plan_manage/src/scan_replan_fsm.cpp');path=TARGET/fsm
    before=path.read_text();after=once(before,'      replan_fail_count_ = 0;\n      need_hover_stop_ = true;',
        '      publishP2BAdmission("rejected", "native_replan_exhausted");\n      replan_fail_count_ = 0;\n      need_hover_stop_ = true;')
    path.write_text(after)
    patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v10/'+str(fsm),tofile='v11/'+str(fsm)))
    receiver=BASE/'runtime_sources/backend_ros/p2b_backend_ros/node.py'
    receipt=BASE/'setup/runtime_sources.json'
    for p in [receiver,receipt]:
        dest=HERE/'parent_source'/p.relative_to(BASE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    before=receiver.read_text()
    anchor='        with self._condition:\n            self._admissions.append(admission)\n            self._condition.notify_all()'
    after=once(before,anchor,'''        owner = self.gate.owner
        if (admission.status == "rejected" and admission.consumer == "fsm"
                and admission.message == "native_replan_exhausted"
                and owner is not None and owner.matches(admission.identity)
                and not self.gate.cancel_pending):
            # The existing runtime fault flow obtains controller hold and
            # measured quiescence; this notice does not claim a physical stop.
            self.gate.close("native_replan_exhausted")
            self._last_block_reason = "native_replan_exhausted"
            self._publish_zero()
''' + anchor)
    receiver.write_text(after)
    patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v10/runtime_sources/backend_ros/p2b_backend_ros/node.py',tofile='v11/runtime_sources/backend_ros/p2b_backend_ros/node.py'))
    record=json.loads(receipt.read_text());matches=[r for r in record['records'] if r['path']==str(receiver.relative_to(BASE))]
    if len(matches)!=1 or matches[0]['sha256']!=sha(HERE/'parent_source'/receiver.relative_to(BASE)):raise ValueError('Receiver receipt mismatch')
    r=matches[0];r['archived_sha256']=r['sha256'];r['sha256']=sha(receiver);r['bytes']=receiver.stat().st_size;r['local_modification']='v11: same-owner native replan exhaustion closes existing gate; preimage and patch in versions/v11'
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    native={str(p.relative_to(TARGET)):sha(p) for p in sorted((TARGET/'src').rglob('*')) if p.is_file()}
    (TARGET/'source_sha256.json').write_text(json.dumps(native,indent=2)+'\n')
    (HERE/'changes.patch').write_text(patch)
    for name in ['building_planner.yaml','flat_planner.yaml']:shutil.copyfile(HERE.parent/'v10'/name,HERE/name)
    selected={ROOT/name for name in parent['source_files']}
    selected.update(p for p in (TARGET/'src').rglob('*') if p.is_file());selected.update([TARGET/'source_sha256.json',receiver,receipt])
    selected.update(p for p in HERE.iterdir() if p.is_file());selected.update(p for p in (HERE/'parent_source').rglob('*') if p.is_file())
    records={}
    for p in sorted(selected):
        name=str(p.relative_to(ROOT));records[name]=sha(p);dest=HERE/'source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (HERE/'manifest.json').write_text(json.dumps({'version':'v11','parent':'v10','status':'frozen_unvalidated','frozen_utc':datetime.now(timezone.utc).isoformat(),'change':'Propagate same-owner native replan exhaustion through existing verified stop flow','source_files':records,'changed_files':[str(p.relative_to(ROOT)) for p in [TARGET/fsm,receiver,receipt]],'native_build':str(TARGET.relative_to(ROOT)),'source_snapshot_prefix':'source/','acceptance_plan':'PLAN.md'},indent=2)+'\n')
    for folder in ['build','install']:shutil.copytree(PARENT/folder,TARGET/folder)
    print(json.dumps({'version':'v11','source_files':len(records)}))
if __name__=='__main__':main()
