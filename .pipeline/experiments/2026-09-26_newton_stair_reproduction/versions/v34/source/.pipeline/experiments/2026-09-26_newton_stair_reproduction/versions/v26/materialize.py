"""Apply the one scoped loader change after verifying the frozen parent."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main():
    assert not (HERE / "prepared.json").exists()
    parent = json.loads((HERE.parent / "v25/manifest.json").read_text())
    for name, digest in parent["source_files"].items():
        assert sha(ROOT / name) == digest, name
    config = BASE / "runtime_sources/backend_ros/p2b_backend_ros/config.py"
    identity = BASE / "setup/runtime_sources.json"
    before = {path: path.read_bytes() for path in (config, identity)}
    for path, raw in before.items():
        target = HERE / "parent_source" / path.relative_to(BASE)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    text = config.read_text()
    text = replace_once(text, "    return _drop_none(normalized)",
        "    normalized = _drop_none(normalized)\n"
        "    # Explicit null selects native automatic layers; omission keeps the default.\n"
        "    if \"pct_layer\" in pilot:\n"
        "        normalized[\"map\"][\"pct_layer\"] = pilot[\"pct_layer\"]\n"
        "    return normalized")
    text = replace_once(text,
        "def _deep_update(base: Dict[str, Any], incoming: Mapping[str, Any]) -> None:",
        "def _deep_update(base: Dict[str, Any], incoming: Mapping[str, Any], path: tuple = ()) -> None:")
    text = replace_once(text, "            _deep_update(base[key], value)",
        "            _deep_update(base[key], value, path + (key,))")
    text = replace_once(text, "        elif value is not None:",
        "        elif value is not None or path + (key,) == (\"map\", \"pct_layer\"):")
    config.write_text(text)
    data = json.loads(identity.read_text())
    record = next(row for row in data["records"] if row["path"] == str(config.relative_to(BASE)))
    assert record["sha256"] == hashlib.sha256(before[config]).hexdigest()
    record["archived_sha256"] = record["sha256"]
    record.update(sha256=sha(config), bytes=config.stat().st_size,
        local_modification="v26 preserves explicit map.pct_layer null in ROS and adapter configs; preimage and patch in versions/v26")
    identity.write_text(json.dumps(data, indent=2) + "\n")
    for name in ("building_planner.yaml", "flat_planner.yaml"):
        shutil.copyfile(HERE.parent / "v25" / name, HERE / name)
    patch = "".join("".join(difflib.unified_diff(
        raw.decode().splitlines(True), path.read_text().splitlines(True),
        fromfile="v25/" + str(path.relative_to(BASE)),
        tofile="v26/" + str(path.relative_to(BASE)))) for path, raw in before.items())
    (HERE / "changes.patch").write_text(patch)
    (HERE / "prepared.json").write_text(json.dumps({
        "parent": "v25", "status": "unfrozen_candidate", "native_build": parent["native_build"],
        "changed_files": [str(path.relative_to(ROOT)) for path in before],
        "config_before_sha256": hashlib.sha256(before[config]).hexdigest(),
        "config_after_sha256": sha(config),
    }, indent=2) + "\n")
    print("v26 loader candidate prepared; validation pending")


if __name__ == "__main__":
    main()
