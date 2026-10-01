"""Freeze a reviewed component candidate; never claim full-scene 30 Hz."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from candidate_identity import candidate_identity

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
ROOT=BASE.parents[2]
NATIVE=BASE/"runtime/scan67_nav2_contract_v36"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--attempt",type=int,required=True)
    args=parser.parse_args()
    assert not (HERE/"manifest.json").exists()
    subprocess.run([sys.executable,str(HERE/"check_source.py")],check=True)
    native=json.loads((HERE/"native_source_sha256.json").read_text())
    assert all(sha(NATIVE/name)==digest for name,digest in native.items())
    assert json.loads((NATIVE/"source_sha256.json").read_text())==native
    build=json.loads((HERE/"build_evidence_retry02/build_result.json").read_text())
    assert build["passed"] and build["source_unchanged"]
    assert json.loads((HERE/"build_evidence_retry02/source_sha256.json").read_text())==native
    install=json.loads((HERE/"build_evidence_retry02/install_sha256.json").read_text())
    assert json.loads((NATIVE/"install_sha256.json").read_text())==install
    assert json.loads((NATIVE/"build_result.json").read_text())==build
    assert all(sha(NATIVE/name)==digest for name,digest in install.items()), "Returned install mismatch"
    attempt=HERE/f"tests/attempt{args.attempt:02d}"
    evidence=json.loads((attempt/"result.json").read_text())
    assert evidence["exit_code"]==0 and evidence["native_passed"] and evidence["backend_tests_passed"]
    assert evidence["source_unchanged"] and evidence["cleanup"]["confirmed_not_running"]
    request=json.loads((attempt/"request.json").read_text())
    assert request["native_source_sha256"]==native
    for name,digest in request["source_sha256"].items():assert sha(ROOT/name)==digest,name
    for name,digest in request["config"].items():assert sha(HERE/name)==digest,name
    assert json.loads((attempt/"global_native_result.json").read_text())["passed"]
    launch_gate=json.loads((HERE/"launch_gate_test_remote.json").read_text())
    assert launch_gate["passed"] and launch_gate["source_sha256"]==sha(HERE/"run_local_episode.py")
    assert launch_gate["test_sha256"]==sha(HERE/"test_launch_gate.py")
    assert len(evidence["recorded_native_plan_measurements"])==2
    for state in ("v33_stand","v32_stand"):
        for mode in ("verify_old","convert_new"):
            records=json.loads((attempt/state/(mode+".json")).read_text())
            assert len(records)==2 and all(row["recorded_fields_unchanged"] for row in records)
    for directory in (attempt,HERE/"build_evidence_retry02"):
        records=json.loads((directory/"return_manifest.json").read_text())
        assert all(sha(ROOT/name)==row["sha256"] and (ROOT/name).stat().st_size==row["bytes"]
                   for name,row in records.items()), "Returned evidence changed"
    review_payload=candidate_identity()
    assert review_payload==json.loads((HERE/"review_identity.json").read_text())
    for name in ("spec","standards"):
        reviewed=json.loads((HERE/"reviews"/(name+".json")).read_text())
        assert reviewed["passed"] and reviewed["reviewed_identity"]==review_payload,name
    parent=json.loads((HERE.parent/"v35/manifest.json").read_text())
    selected=dict(parent["source_files"])
    selected.update({str((NATIVE/name).relative_to(ROOT)):digest for name,digest in native.items()})
    selected.update({str((NATIVE/name).relative_to(ROOT)):sha(NATIVE/name) for name in
                     ("source_sha256.json","install_sha256.json","build_result.json")})
    for path in HERE.rglob("*"):
        if (not path.is_file() or path.is_symlink() or "source" in path.relative_to(HERE).parts or "probe_build" in path.parts or "__pycache__" in path.parts or
            path.name in {"RESULTS.md","LOCAL_ONLY_BYTES.json","manifest.json","quality.json"}):continue
        selected[str(path.relative_to(ROOT))]=sha(path)
    for name,entry in json.loads((HERE/"recorded_input_manifest.json").read_text()).items():
        assert sha(ROOT/name)==entry["sha256"]
        selected[name]=entry["sha256"]
    identity=BASE/"repairs/2026-09-26_generic_occupancy/candidate67_nav2_contract_v36_identity.json"
    assert not identity.exists()
    identity.write_text(json.dumps({"integration_version":"v36","parent":"v35","source_sha256":native,
        "native_build":str(NATIVE.relative_to(ROOT)),"claim":"Component-tested configuration; recorded local plans exceed 30 Hz budget; full-scene rate/navigation unvalidated"},indent=2)+"\n")
    selected[str(identity.relative_to(ROOT))]=sha(identity)
    for name,digest in selected.items():
        path=ROOT/name
        assert sha(path)==digest,name
        destination=HERE/"source"/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination)
        assert sha(destination)==digest
    manifest={"version":"v36","parent":"v35","status":"frozen_component_candidate","source_files":dict(sorted(selected.items())),
        "native_source_sha256":native,"native_install_sha256":install,"configuration":json.loads((HERE/"navigation_contract.json").read_text()),
        "component_evidence":str(attempt.relative_to(ROOT)),"physics_run":False,"navigation_validated":False,
        "local_planning_30hz_validated":False,"navigation_contract_fully_validated":False,
        "recorded_native_plan_measurements":evidence["recorded_native_plan_measurements"],
        "claim":"Global/controller rates measured in components; nominal local scheduling and goal checks tested; recorded local plans overrun the 30 Hz budget. Full-scene real-time/navigation unvalidated."}
    (HERE/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"frozen_files":len(selected),"version":"v36","physics_run":False,"navigation_validated":False}))


if __name__=="__main__":main()
