"""Use the existing PCT projection/clock publisher with a registered long floor."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pickle

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "repairs/2026-09-27_pd_long_route/inputs"
source = BASE / "repairs/2026-09-26_generic_occupancy/flat_support_publisher.py"
identity = json.loads(source.with_name("flat_publisher_identity.json").read_text())
if hashlib.sha256(source.read_bytes()).hexdigest() != identity["output_sha256"]:
    raise ValueError("Existing flat publisher identity mismatch")
spec = importlib.util.spec_from_file_location("existing_flat_publisher", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def load_map(path):
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if path.resolve() != (ROOT / "flat_floor.pickle").resolve():
        raise ValueError("Unregistered long floor")
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files"]["flat_floor.pickle"]:
        raise ValueError("Long floor identity mismatch")
    with path.open("rb") as stream:
        return pickle.load(stream)


if __name__ == "__main__":
    module.load_registered_flat_map = load_map
    module.main()
