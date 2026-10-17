"""Fetch pinned public source text for a read-only UAS audit; run no upstream code."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parent
UAS = ROOT / "source/unified_autonomy_stack"
WANTED = {"robot_bringup", "gbplanner_ros", "pci_general", "mimosa",
          "sdf_nmpc_ros", "sdf-nmpc", "rl_nav", "ugv_gz",
          "composite_cbf", "cbf_pc_selector"}
EXCLUDE = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".mp4", ".mov", ".bag",
           ".db3", ".mcap", ".pt", ".pth", ".onnx", ".zip", ".gz", ".tgz",
           ".pcd", ".ply", ".stl", ".dae", ".obj", ".npy", ".npz", ".bin"}

def fetch(item):
    name, url, pin, manifest = item
    dest = ROOT / "source" / name
    logs = []
    env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"}
    def git(*args, stdin=None):
        proc = subprocess.run(["git", "-C", str(dest), *args], input=stdin,
                              text=True, capture_output=True, env=env, timeout=120)
        logs.append({"argv": list(args), "returncode": proc.returncode,
                     "stdout": proc.stdout, "stderr": proc.stderr})
        if proc.returncode:
            raise RuntimeError(proc.stderr[-1000:])
        return proc.stdout.strip()
    result = {"name": name, "url": url, "pin": pin, "uas_manifest": manifest}
    try:
        dest.mkdir(exist_ok=True)
        if not (dest / ".git").exists():
            git("init", "-q")
            git("remote", "add", "origin", url)
        git("fetch", "--depth=1", "--filter=blob:none", "origin", pin)
        paths = git("ls-tree", "-r", "--name-only", "FETCH_HEAD").splitlines()
        selected = [p for p in paths if Path(p).suffix.lower() not in EXCLUDE]
        git("sparse-checkout", "init", "--no-cone")
        git("sparse-checkout", "set", "--no-cone", "--stdin",
            stdin="\n".join("/" + p for p in selected) + "\n")
        git("checkout", "--detach", "FETCH_HEAD")
        result.update(status="acquired_not_executed", actual_commit=git("rev-parse", "HEAD"),
                      commit_date=git("show", "-s", "--format=%cI", "HEAD"),
                      total_tree_paths=len(paths), selected_text_paths=len(selected),
                      excluded_paths=[p for p in paths if p not in selected])
    except Exception as exc:
        result.update(status="fetch_error", error=str(exc))
    (ROOT / "raw_logs" / (name + "_acquisition.json")).write_text(json.dumps(logs, indent=2) + "\n")
    return result

if __name__ == "__main__":
    found = {}
    for manifest in sorted((UAS / "repos").glob("*_exact.repos")):
        text = manifest.read_text()
        for url, pin in re.findall(r"url:\s*(\S+)\s+version:\s*(\S+)", text):
            name = url.rsplit("/", 1)[-1].removesuffix(".git")
            if name in WANTED:
                url = url.replace("git@github.com:", "https://github.com/")
                found[name] = (name, url, pin, str(manifest.relative_to(UAS)))
    assert set(found) == WANTED, set(found)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, found.values()))
    (ROOT / "acquisition.json").write_text(json.dumps(results, indent=2) + "\n")
    for result in results:
        print(result["name"], result["status"], result.get("actual_commit", result.get("error")))
