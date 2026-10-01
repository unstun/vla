"""P1 on gpu5070ti: the pre-physics gates of scripts/run_local_episode.py, executed on the execution copy.
The version gate (verify_integration_version, lines 62-77) and the record gate (lines 163-165) are executed from their
own source text; the native-build identity is checked as freeze.py and the launcher do (source_sha256.json)."""
import ast, hashlib, json, sys
from pathlib import Path
R = Path.home() / "vla_exec/vla"
BASE = R / ".pipeline/experiments/2026-09-26_newton_stair_reproduction"
src = (BASE / "scripts/run_local_episode.py").read_text()
lines = src.splitlines()
out = {}
# version gate: run the function's own text against a scratch output directory
tree = ast.parse(src)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "verify_integration_version")
ns = {"BASE": BASE, "PROJECT": R, "json": json, "hashlib": hashlib, "shutil": __import__("shutil")}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "verify_integration_version", "exec"), ns)
scratch = Path.home() / "vla_exec/port/p1_scratch_v35"
scratch.mkdir(parents=True, exist_ok=True)
try:
    out["version_gate"] = {"passed": ns["verify_integration_version"](scratch, "v35") == "v35"}
except Exception as exc:
    out["version_gate"] = {"passed": False, "error": str(exc)}
# record gate: lines 163-165 verbatim
block = "\n".join(l[4:] for l in lines[162:165])
assert block.startswith('for record in json.loads((BASE / "setup/runtime_sources.json")'), block
try:
    exec(block, {"BASE": BASE, "json": json, "hashlib": hashlib})
    out["record_gate"] = {"passed": True, "records": len(json.loads((BASE / "setup/runtime_sources.json").read_text())["records"])}
except Exception as exc:
    out["record_gate"] = {"passed": False, "error": str(exc)}
# native build identity
N = BASE / "runtime/scan66_periodic_replan_v35"
# both manifests the launcher checks (lines 152-155); install_sha256.json was added after P6's first attempt found
# the build's __pycache__ files missing from the copy
bad, counts = [], {}
for name in ("source_sha256.json", "install_sha256.json"):
    manifest = json.loads((N / name).read_text())
    counts[name] = len(manifest)
    bad += [n for n, d in manifest.items() if not (N / n).is_file() or hashlib.sha256((N / n).read_bytes()).hexdigest() != d]
out["native_identity"] = {"passed": not bad and json.loads((N / "build_result.json").read_text())["passed"],
                          "files": counts, "mismatches": bad}
# reviewed candidate (run_local_episode.py lines 158-162, applied to geometry-only episodes such as the trial)
identities = [json.loads(p.read_text()) for p in (BASE / "repairs/2026-09-26_generic_occupancy").glob("candidate*identity*.json")]
out["reviewed_candidate"] = {"passed": any(json.loads((N / "source_sha256.json").read_text()) == i["source_sha256"] for i in identities),
                             "identities_checked": len(identities)}
import shutil
out["free_disk"] = {"passed": shutil.disk_usage(BASE).free >= 10 * 1024**3, "free_gib": round(shutil.disk_usage(BASE).free / 1024**3, 1)}
# scene inputs as scene_assets.verify_inputs checks them
ident = json.loads((BASE / "setup/source_identity.json").read_text())
bad = [i["path"] for i in ident["inputs"] if hashlib.sha256((BASE / i["path"]).read_bytes()).hexdigest() != i["sha256"]]
out["scene_inputs"] = {"passed": not bad, "inputs": len(ident["inputs"]), "mismatches": bad}
out["passed"] = all(v["passed"] for v in out.values())
print(json.dumps(out, indent=2))
