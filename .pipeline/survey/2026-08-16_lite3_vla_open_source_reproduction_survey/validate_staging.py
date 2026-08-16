#!/usr/bin/env python3
"""Validate the internal structure of the staged Lite3 VLA survey.

This script does not access the network and does not run any upstream project.
It checks only staged metadata, local links, PDF signatures, hashes, and status fields.
"""
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "Users/sun/vla/.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md"
LITERATURE = ROOT / "Users/sun/vla/.pipeline/literature/2026-08-16_surveyed_append.md"
PAPER_DIR = ROOT / "Users/sun/vla/docs/research/papers"

failures: list[str] = []
checks = 0


def require(condition: bool, label: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(label)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


for path in [
    REPORT,
    LITERATURE,
    ROOT / "audit/paper_pdf_manifest.tsv",
    ROOT / "audit/repository_audit.tsv",
    ROOT / "audit/top5_code_evidence.tsv",
    ROOT / "audit/source_register.tsv",
    ROOT / "audit/search_log.md",
    ROOT / "UNAPPLIED_PROJECT_ACTIONS.md",
    ROOT / "README.md",
]:
    require(path.is_file(), f"missing file: {path.relative_to(ROOT)}")

report = REPORT.read_text(encoding="utf-8")
expected_frontmatter = "---\norigin: ai_only\nreviewed: false\nas_of: 2026-08-16\n---\n"
require(report.startswith(expected_frontmatter), "main report frontmatter differs")
require(report.count("```") % 2 == 0, "unbalanced Markdown code fences")
for text in [
    "本轮最推荐先复现 `OmniVLA`",
    "备选是 `InternVLA-N1 / InternNav`",
    "第三名 `VLFM` 也不应先做",
    "`surveyed`，不是 `reproduced`",
    "本轮没有运行任何候选项目的安装、推理、仿真、训练或真机命令",
    "未经 Dr Sun 选择，不导入代码",
]:
    require(text in report, f"required report statement missing: {text}")

headings = [line for line in report.splitlines() if line.startswith("#")]
require(len(headings) == len(set(headings)), "duplicate Markdown headings")

repos = read_tsv(ROOT / "audit/repository_audit.tsv")
require(len(repos) == 21, f"repository rows: expected 21, got {len(repos)}")
for row in repos:
    require(row.get("status") == "surveyed", f"repository status not surveyed: {row.get('name')}")
    require(row.get("checked_on") == "2026-08-16", f"repository check date mismatch: {row.get('name')}")
    commit = row.get("commit", "")
    require(commit == "—" or re.fullmatch(r"[0-9a-f]{40}", commit) is not None, f"invalid commit: {row.get('name')}={commit}")

top5_path = ROOT / "audit/top5_code_evidence.tsv"
with top5_path.open(encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    top5 = list(reader)
    top5_fields = reader.fieldnames or []
require(len(top5) == 5, f"Top 5 rows: expected 5, got {len(top5)}")
require(len(top5_fields) == 39, f"Top 5 fields: expected 39, got {len(top5_fields)}")
for row in top5:
    require(row.get("evidence_status") == "surveyed", f"Top 5 status not surveyed: {row.get('name')}")
    require(re.fullmatch(r"[0-9a-f]{40}", row.get("pinned_commit", "")) is not None, f"Top 5 invalid commit: {row.get('name')}")

sources = read_tsv(ROOT / "audit/source_register.tsv")
require(len(sources) == 46, f"source rows: expected 46, got {len(sources)}")
require([row["source_id"] for row in sources] == [f"S{i:03d}" for i in range(1, 47)], "source IDs are not sequential")
require(all(row.get("status") == "surveyed" for row in sources), "source status not uniformly surveyed")

manifest = read_tsv(ROOT / "audit/paper_pdf_manifest.tsv")
require(len(manifest) == 24, f"PDF manifest rows: expected 24, got {len(manifest)}")
require(len(list(PAPER_DIR.glob("*.pdf"))) == 24, "PDF directory count differs from 24")
for row in manifest:
    path = PAPER_DIR / row["filename"]
    require(path.is_file(), f"missing PDF: {row['filename']}")
    if not path.is_file():
        continue
    data = path.read_bytes()
    require(data.startswith(b"%PDF-"), f"invalid PDF signature: {row['filename']}")
    require(hashlib.sha256(data).hexdigest() == row["sha256"], f"PDF SHA-256 mismatch: {row['filename']}")
    require(row.get("status") == "surveyed", f"PDF status not surveyed: {row['filename']}")
    result = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
    require(result.returncode == 0, f"pdfinfo failed: {row['filename']}")
    if result.returncode == 0:
        pages = next((line.split(":", 1)[1].strip() for line in result.stdout.splitlines() if line.startswith("Pages:")), "")
        require(pages == row["pages"], f"PDF page count mismatch: {row['filename']}")

for target in re.findall(r"\]\(([^)]+\.pdf)\)", report):
    require((REPORT.parent / target).resolve().is_file(), f"broken report PDF link: {target}")

literature = LITERATURE.read_text(encoding="utf-8")
require(len(re.findall(r"^## (?!Repository:)", literature, re.MULTILINE)) == 24, "literature paper record count differs from 24")
require(len(re.findall(r"^## Repository:", literature, re.MULTILINE)) == 21, "literature repository record count differs from 21")
require(literature.count("evidence_status: surveyed") == 45, "literature surveyed status count differs from 45")
for rel in re.findall(r"- local_pdf: `([^`]+)`", literature):
    require((ROOT / "Users/sun/vla" / rel).is_file(), f"broken literature PDF path: {rel}")

if failures:
    print(f"FAIL: {len(failures)} of {checks} checks failed", file=sys.stderr)
    for failure in failures:
        print(f"- {failure}", file=sys.stderr)
    raise SystemExit(1)

print(f"PASS: {checks} internal checks; status remains surveyed; no upstream execution was performed")
