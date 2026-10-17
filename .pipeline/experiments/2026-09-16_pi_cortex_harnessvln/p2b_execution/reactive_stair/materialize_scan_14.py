"""Let native reactive A-star search height instead of one endpoint plane."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_13"
OUT = HERE.parent / "builds/scan_14"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_13 source/build gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    path = OUT / "src/path_searching/src/dyn_a_star.cpp"
    source = path.read_bytes()
    start = source.index(b'    const Eigen::Vector3d search_start = Index2Coord(start_idx);')
    end = source.index(b'    // if ( start_pt(0)', start)
    source = source[:start] + source[end:]
    replacements = [
        (b'            for (int dy = -1; dy <= 1; dy++)\r\n            {\r\n                if (dx == 0 && dy == 0)',
         b'            for (int dy = -1; dy <= 1; dy++)\r\n              for (int dz_step = -1; dz_step <= 1; dz_step++)\r\n            {\r\n                if (dx == 0 && dy == 0 && dz_step == 0)'),
        (b'                neighborIdx(2) = interpolateZIndexOnSearchPlane(neighborIdx(0), neighborIdx(1));',
         b'                neighborIdx(2) = current->index(2) + dz_step;'),
        (b'                const double neighbor_yaw = std::atan2(static_cast<double>(dy), static_cast<double>(dx));',
         b'''                const double neighbor_yaw = (dx == 0 && dy == 0)
                    ? std::atan2(end_pt.y() - start_pt.y(), end_pt.x() - start_pt.x())
                    : std::atan2(static_cast<double>(dy), static_cast<double>(dx));''')]
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError("A-star anchor changed: " + repr(old[:60]))
        source = source.replace(old, new, 1)
    path.write_bytes(source)
    manifest = {"base": "scan_13", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(path.relative_to(OUT)): sha(path)},
                "problem": "one interpolated Z per XY prevents detours that must rise with stair support",
                "change": "26-neighbor 3D search; pure vertical edges use the endpoint heading",
                "preserved": "same conservative collision query including support height, unknown space, current people, freshness; same resolution, search time cap and optimizer"}
    (OUT / "vertical_search_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
