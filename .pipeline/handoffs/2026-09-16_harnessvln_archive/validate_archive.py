#!/usr/bin/env python3
"""Check local archive state, links, snapshots and recorded integrity gates."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(path):
    return json.loads(path.read_text())


checks = {}
hot_counts = {}
for name, chars, lines in [('状态简报.md', 1500, 30), ('未关闭决策.md', 1200, 25), ('近期改动.md', 1000, 25)]:
    path = ROOT / 'bigmemory/热区' / name
    text = path.read_text()
    hot_counts[name] = {'characters': len(text), 'lines': len(text.splitlines())}
    checks['hot_budget_' + name] = len(text) <= chars and len(text.splitlines()) <= lines
recent = (ROOT / 'bigmemory/热区/近期改动.md').read_text()
checks['recent_daily_entries'] = sum(line.startswith('- ') for line in recent.splitlines()) <= 3
snapshots = load(HERE / 'pre_archive_hot_zone_manifest.json')
checks['prior_hot_bytes_preserved'] = all(hashlib.sha256((ROOT / row['snapshot']).read_bytes()).hexdigest() == row['sha256'] for row in snapshots)
degradation = load(HERE / 'cold_degradation.json')
preserved = []
for row in degradation['processed']:
    text = (ROOT / row['path']).read_text()
    original = re.sub(r'\n\n> \[摘要\].*\n> 2026-09-16 达到 31 天归档阈值；以下历史原文完整保留。', '', text, count=1)
    preserved.append(hashlib.sha256(original.encode()).hexdigest() == row['original_sha256'])
checks['aged_original_text_preserved'] = all(preserved)
checks['knowledge_gate_passed'] = load(HERE / 'knowledge_gate.json')['pass']
returns = load(HERE / 'returned_artifact_validation.json')
checks['returned_artifacts_match'] = all(row['match'] for row in returns) and sum(row['artifacts'] for row in returns) == 207
bundle = load(HERE / 'bundle_validation.json')
checks['bundle_members_verified'] = bundle['all_members_match'] and bundle['archive_sha256_match']
task = load(ROOT / '.trellis/tasks/09-16-emos-harnessvln-reimplementation/task.json')
checks['task_boundary_retained'] = task['status'] == 'in_progress' and not task['meta']['scan_resubmit_diagnosis']['production_change_adopted'] and not task['meta']['scan_resubmit_diagnosis']['patched_isaac_validated']
checks['claude_wrapper_preserved'] = (ROOT / 'CLAUDE.md').read_text() == '@AGENTS.md\n'
docs = [ROOT / '.pipeline/handoffs/2026-09-16_harnessvln_local_archive.md', ROOT / '.pipeline/handoffs/2026-09-16_harnessvln_archive_report.md', ROOT / '.pipeline/experiments/README.md']
docs.extend((ROOT / 'bigmemory/热区').glob('*.md'))
for folder in ['改动记录', '踩坑记录', '心路历程', '里程碑']:
    docs.append(ROOT / 'bigmemory/冷区' / folder / '2026-09-16.md')
missing = []
count = 0
for doc in docs:
    for target in re.findall(r'\[[^\]]*\]\(([^)\n]+)\)', doc.read_text()):
        if target.startswith(('http:', 'https:', '#', 'codex:')):
            continue
        target = target.strip('<>').split('#')[0]
        path = Path(target) if target.startswith('/') else doc.parent / target
        count += 1
        if not path.exists():
            missing.append({'document': str(doc.relative_to(ROOT)), 'target': target})
checks['archive_links_resolve'] = not missing
result = {'passed': all(checks.values()), 'checks': checks, 'hot_counts': hot_counts,
          'checked_local_links': count, 'missing_links': missing,
          'dedicated_project_harness_validator': 'No dedicated script found; JSON/state/link/source-hash/wrapper/byte-preservation checks performed here.'}
(HERE / 'validation.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(result, indent=2, ensure_ascii=False))
raise SystemExit(0 if result['passed'] else 1)
