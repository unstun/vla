"""Collect small, pinned public source references; never build or execute them."""
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / 'references/upstream/2026-10-09_navigation_qualification'
REPOS = [
    'wuyi2121/SCAN-Planner', 'byangw/PCT_planner',
    'leggedrobotics/art_planner', 'jizhang-cmu/autonomy_stack_go2',
    'leggedrobotics/viplanner', 'leggedrobotics/fdm',
    'WangJinCheng1998/sandplanner', 'ori-drs/field_local_planner',
    'ZJU-FAST-Lab/ego-planner', 'ZJU-FAST-Lab/EGO-Planner-v2',
    'HKUST-Aerial-Robotics/Fast-Planner', 'mit-acl/faster',
    'rst-tu-dortmund/teb_local_planner', 'ros-navigation/navigation2',
    'ros-planning/navigation', 'ignc-research/arena-bench',
    'SlyPredator/the-barn-challenge', 'thu-uav/FlightBench',
]


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'vla-qualification-source-audit'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def collect(repo):
    directory = DEST / 'source' / repo.replace('/', '__')
    directory.mkdir(parents=True, exist_ok=True)
    existing = directory / 'metadata.json'
    if existing.exists():
        return json.loads(existing.read_text())
    info = json.loads(get(f'https://api.github.com/repos/{repo}'))
    canonical = info['full_name']
    pin = subprocess.check_output(
        ['git', 'ls-remote', f'https://github.com/{canonical}.git', 'HEAD'],
        text=True, timeout=45).split()[0]
    tree = json.loads(get(f'https://api.github.com/repos/{canonical}/git/trees/{pin}?recursive=1'))
    paths = [item['path'] for item in tree['tree'] if item['type'] == 'blob']
    (directory / 'tree_paths.txt').write_text('\n'.join(paths) + '\n')
    root_files = [p for p in paths if '/' not in p]
    selection = [p for p in root_files if p.lower().startswith(('readme', 'license', 'copying'))]
    files = []
    for path in selection:
        url = f'https://raw.githubusercontent.com/{canonical}/{pin}/{path}'
        raw = get(url)
        if len(raw) > 250_000:
            continue
        (directory / path).write_bytes(raw)
        files.append(dict(path=path, url=url, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    result = dict(requested_repository=repo, canonical_repository=canonical,
                  canonical_url=info['html_url'], homepage=info.get('homepage'),
                  default_branch=info['default_branch'], pinned_commit=pin,
                  archived=info['archived'], fork=info['fork'], pushed_at=info['pushed_at'],
                  license_api=info.get('license'), tree_truncated=tree.get('truncated'),
                  file_count=len(paths), files=files, status='surveyed', reproduction='not_run',
                  local_modifications=[], selected_source_path=str(directory.relative_to(ROOT)))
    existing.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {pool.submit(collect, repo): repo for repo in REPOS}
        results = []
        for task in concurrent.futures.as_completed(tasks):
            repo = tasks[task]
            try:
                row = task.result()
                results.append(row)
                print(repo, row['pinned_commit'][:12], row['file_count'], flush=True)
            except Exception as error:
                results.append(dict(requested_repository=repo, error=str(error)))
                print(repo, 'ERROR', str(error), flush=True)
    (DEST / 'manifest.json').write_text(json.dumps(results, indent=2) + '\n')
