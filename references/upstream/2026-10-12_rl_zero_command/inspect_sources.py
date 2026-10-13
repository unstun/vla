"""Read-only upstream inspection; downloaded Python is never executed."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
REPOS = ["fan-ziqi/robot_lab", "unitreerobotics/unitree_rl_lab",
         "unitreerobotics/unitree_rl_mjlab", "Improbable-AI/walk-these-ways",
         "isaac-sim/IsaacLab"]


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "vla-zero-command-source-survey"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def discover(repo):
    dest = ROOT / "source" / repo.replace("/", "__")
    if (dest / "metadata.json").exists():
        return json.loads((dest / "metadata.json").read_text())
    info = json.loads(get("https://api.github.com/repos/" + repo))
    commit = json.loads(get("https://api.github.com/repos/" + repo + "/commits/" + info["default_branch"]))
    sha = commit["sha"]
    tree = json.loads(get("https://api.github.com/repos/" + repo + "/git/trees/" + sha + "?recursive=1"))
    assert not tree.get("truncated"), repo
    paths = [x["path"] for x in tree["tree"] if x["type"] == "blob"]
    meta = dict(repository=repo, canonical_url=info["html_url"], default_branch=info["default_branch"],
                pinned_commit=sha, license=info.get("license"), archived=info["archived"],
                pushed_at=info["pushed_at"], inspected_at=datetime.now(timezone.utc).isoformat(),
                status="surveyed", upstream_executed=False)
    dump(dest / "metadata.json", meta)
    (dest / "tree_paths.txt").write_text("\n".join(paths) + "\n")
    return meta


def fetch(item):
    repo, paths = item
    dest = ROOT / "source" / repo.replace("/", "__")
    meta = json.loads((dest / "metadata.json").read_text())
    available = set((dest / "tree_paths.txt").read_text().splitlines())
    manifest = json.loads((dest / "files.json").read_text()) if (dest / "files.json").exists() else []
    records = {x["path"]: x for x in manifest}
    for path in paths:
        assert path in available, (repo, path)
        url = "https://raw.githubusercontent.com/" + repo + "/" + meta["pinned_commit"] + "/" + path
        raw = get(url)
        assert len(raw) < 2_000_000, path
        raw.decode("utf-8")
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        records[path] = dict(path=path, url=url, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    dump(dest / "files.json", list(records.values()))
    return {"repository": repo, "commit": meta["pinned_commit"], "files": len(records)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["discover", "fetch"])
    args = parser.parse_args()
    items = REPOS if args.mode == "discover" else list(json.loads((ROOT / "selection.json").read_text()).items())
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(discover if args.mode == "discover" else fetch, items):
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
