"""Save small, commit-pinned GitHub inspection records; never execute upstream code."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
REPOS = [
    "InternRobotics/InternNav", "InternRobotics/NavDP", "AnjieCheng/NaVILA",
    "yang-zj1026/legged-loco", "yang-zj1026/NaVILA-Bench", "NHirose/OmniVLA",
    "ucla-mobility/TIC-VLA", "amap-cvlab/OmniNav", "amap-cvlab/ABot-Navigation",
    "QwenLM/Qwen-RobotNav", "PKU-EPIC/NavFoM-Web", "leggedrobotics/viplanner",
    "rai-opensource/vlfm", "jzhzhang/Uni-NaVid", "AIprogrammer/ReflectVLN",
    "AIGeeksGroup/MobileVLA-R1", "wsakobe/VLingNav-web",
]

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "VLA-source-survey", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read()

def inspect(repo):
    destination = ROOT / repo.replace("/", "__")
    destination.mkdir(exist_ok=True)
    log = {"repository": repo, "checked_at": datetime.now(timezone.utc).isoformat(), "sources": []}
    def save(url, name):
        data = get(url)
        (destination / name).write_bytes(data)
        log["sources"].append({"url": url, "file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        return data
    try:
        meta = json.loads(save(f"https://api.github.com/repos/{repo}", "metadata.json"))
        branch = meta["default_branch"]
        commit = json.loads(save(f"https://api.github.com/repos/{repo}/commits/{branch}", "head.json"))
        sha = commit["sha"]
        log.update(branch=branch, commit=sha, commit_date=commit["commit"]["committer"]["date"], license=(meta.get("license") or {}).get("spdx_id"), archived=meta["archived"], open_issues_count=meta["open_issues_count"])
        try:
            save(f"https://raw.githubusercontent.com/{repo}/{sha}/README.md", "README.md")
        except Exception:
            save(f"https://raw.githubusercontent.com/{repo}/{sha}/readme.md", "README.md")
    except Exception as error:
        log["error"] = str(error)
    (destination / "inspection.json").write_text(json.dumps(log, indent=2) + "\n")
    return log

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(inspect, REPOS))
    (ROOT / "github_inventory.json").write_text(json.dumps(results, indent=2) + "\n")
    for item in results:
        print(json.dumps({key: value for key, value in item.items() if key != "sources"}))
