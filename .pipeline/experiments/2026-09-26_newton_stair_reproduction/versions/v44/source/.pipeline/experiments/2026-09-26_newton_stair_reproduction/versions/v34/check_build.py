"""K1 (PLAN.md): the materialization is byte-exact and the scan65 build differs from scan64 only where expected.

- Patch: changes.patch is applied, as an insert-only unified diff, to parent_source/ (scan64's bytes of the two edited
  files) and to an empty file for the new header. The results must equal scan65's three files byte for byte,
  including CRLF line endings, and every other scan65 source file must equal scan64's.
- Build: the translation units scan65's build recompiled (build.log), the installed files whose SHA-256 differs from
  scan64's (install_sha256.json), and the compiler warnings of both builds compared as a multiset of
  (file, line, column, message). No warning may be new, and none may name the new header or supportGround.
Writes check_build.json.
"""
from pathlib import Path
import collections
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
OLD = BASE / "runtime/scan64_input_refresh_v31"
NEW = BASE / "runtime/scan65_evidence_floor_v34"
sha = lambda data: hashlib.sha256(data).hexdigest()


def split_files(patch):
    """Yield (target, hunks) per file of a unified diff kept as surrogate-escaped text with its line endings."""
    lines = patch.splitlines(True)
    i = 0
    while i < len(lines):
        assert lines[i].startswith("--- "), lines[i][:40]
        target = lines[i + 1][4:].rstrip("\r\n")
        i += 2
        hunks = []
        while i < len(lines) and lines[i].startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
            old_start = int(m.group(1))
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith(("@@", "--- ")):
                body.append(lines[i])
                i += 1
            hunks.append((old_start, body))
        yield target, hunks


def apply(before_lines, hunks):
    out, cursor = [], 0
    for old_start, body in hunks:
        start = max(old_start - 1, 0) if before_lines else 0
        out += before_lines[cursor:start]
        cursor = start
        for line in body:
            tag, text = line[0], line[1:]
            if tag == " ":
                assert before_lines[cursor] == text, (cursor, text[:40])
                out.append(text)
                cursor += 1
            elif tag == "+":
                out.append(text)
            else:
                raise AssertionError("insert-only patch expected, found " + repr(line[:40]))
    return out + before_lines[cursor:]


patch = (HERE / "changes.patch").read_bytes().decode("utf-8", "surrogateescape")
patched = {}
for target, hunks in split_files(patch):
    relative = target.split("/", 1)[1]
    preimage = HERE / "parent_source" / relative
    before = preimage.read_bytes().decode("utf-8", "surrogateescape").splitlines(True) if preimage.exists() else []
    after = "".join(apply(before, hunks)).encode("utf-8", "surrogateescape")
    patched[relative] = sha(after) == sha((NEW / relative).read_bytes())
old_manifest = json.loads((OLD / "source_sha256.json").read_text())
new_manifest = json.loads((NEW / "source_sha256.json").read_text())
others_equal = all(new_manifest[name] == old_manifest[name] for name in new_manifest if name not in patched)


def installed(tree):
    return json.loads((tree / "install_sha256.json").read_text())


old_install, new_install = installed(OLD), installed(NEW)
changed_install = sorted(name for name in set(old_install) | set(new_install) if old_install.get(name) != new_install.get(name))
WARNING = re.compile(r"^(/workspace/\S+?):(\d+):(\d+): warning: (.*)$")


def warnings(tree):
    counts = collections.Counter()
    for line in (tree / "build.log").read_text(errors="replace").splitlines():
        m = WARNING.match(line)
        if m:
            counts[m.groups()] += 1
    return counts


old_warnings, new_warnings = warnings(OLD), warnings(NEW)
new_only = new_warnings - old_warnings
recompiled = sorted(set(re.findall(r"Building CXX object \S+?/src/([^/\s]+?)\.o", (NEW / "build.log").read_text(errors="replace"))))
result = {
    "patch_reproduces": patched,
    "other_sources_equal_scan64": others_equal,
    "source_files": {"scan64": len(old_manifest), "scan65": len(new_manifest)},
    "build_passed": json.loads((NEW / "build_result.json").read_text())["passed"],
    "build_wall_s": json.loads((NEW / "build_result.json").read_text())["wall_s"],
    "recompiled_translation_units": recompiled,
    "installed_files_changed": changed_install,
    "warnings": {"scan64_total": sum(old_warnings.values()), "scan65_total": sum(new_warnings.values()),
                 "new_in_scan65": [list(k) + [v] for k, v in new_only.items()],
                 "naming_new_code": [list(k) for k in new_warnings if "evidence_floor_fill" in k[0] or "supportGround" in k[3]]},
}
result["passed"] = (all(patched.values()) and len(patched) == 3 and others_equal and result["build_passed"]
                    and not new_only and not result["warnings"]["naming_new_code"])
(HERE / "check_build.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "installed_files_changed"}, indent=1))
print("installed files changed:", changed_install)
