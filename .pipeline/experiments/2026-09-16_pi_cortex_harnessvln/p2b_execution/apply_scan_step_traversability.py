#!/usr/bin/env python3
"""Hash-gated SCAN patch: global step rule in getInflateOccupancy.

Applies to a copy of the scan_04 plan_env sources. Refuses scan_01–scan_04
build names. Does not edit planner.yaml or frozen occupancy keys.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADER_SRC = HERE / "step_traversability.h"
GRID_H_REL = Path("src/plan_env/include/plan_env/grid_map.h")
GRID_CPP_REL = Path("src/plan_env/src/grid_map.cpp")
HEADER_DST_REL = Path("src/plan_env/include/plan_env/step_traversability.h")
SCAN_04_GRID_H_SHA256 = "3a562e007f40dc78fd811b31f4326cf778cfb0e475a1d61fd0836eda3aaa28d4"
SCAN_04_GRID_CPP_SHA256 = "2b94d5e09a71f3d9349e9b816f0b1e42b3dbc03551a20b7452579122e88efc87"
IMMUTABLE_BUILDS = {"scan_01", "scan_02", "scan_03", "scan_04"}
MANIFEST_NAME = "step_traversability_patch_manifest.json"

INCLUDE_ANCHOR = "#include <plan_env/raycast.h>"
INCLUDE_LINE = "#include <plan_env/step_traversability.h>"
PARAM_ANCHOR = "  double double_cylinder_radius_, double_cylinder_offset_;"
PARAM_INSERT = [
    "  bool step_filter_enable_;",
    "  StepTraversabilityParams step_filter_;",
]
DECL_ANCHOR = "  inline int getInflateOccupancyFromBuffer(Eigen::Vector3d pos, const std::vector<char>& buffer);"
DECL_INSERT = [
    "  inline bool columnMaxOccupiedZ(int ix, int iy, double *z_out);",
    "  inline bool queryIsTraversableStep(const Eigen::Vector3d& pos);",
]
CPP_ANCHOR = '  load_parameter(node_, "grid_map.double_cylinder_offset", mp_.double_cylinder_offset_, 0.0);'
CPP_INSERT = [
    '  load_parameter(node_, "grid_map.step_filter_enable", mp_.step_filter_enable_, true);',
    '  load_parameter(node_, "grid_map.step_filter_critical_height", mp_.step_filter_.critical_height_m, 0.26);',
    '  load_parameter(node_, "grid_map.step_filter_window_radius", mp_.step_filter_.window_radius_m, 0.30);',
    '  load_parameter(node_, "grid_map.step_filter_height_band", mp_.step_filter_.height_band_m, 0.05);',
    '  load_parameter(node_, "grid_map.step_filter_min_tread_depth", mp_.step_filter_.min_tread_depth_m, 0.15);',
    '  load_parameter(node_, "grid_map.step_filter_min_step_height", mp_.step_filter_.min_step_height_m, 0.04);',
]
OLD_INFLATE = [
    "inline int GridMap::getInflateOccupancy(Eigen::Vector3d pos, double yaw) {",
    "  Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);",
    "  Eigen::Vector3d front = pos + mp_.double_cylinder_offset_ * heading;",
    "  Eigen::Vector3d rear = pos - mp_.double_cylinder_offset_ * heading;",
    "",
    "  int front_occ = getInflateOccupancyFromBuffer(front, md_.occupancy_buffer_inflate_);",
    "  if (front_occ != 0) return front_occ;",
    "",
    "  return getInflateOccupancyFromBuffer(rear, md_.occupancy_buffer_inflate_);",
    "}",
]
NEW_INFLATE = [
    "inline bool GridMap::columnMaxOccupiedZ(int ix, int iy, double *z_out) {",
    "  bool found = false;",
    "  double z_max = 0.0;",
    "  for (int iz = mp_.map_bound_min_idx_(2); iz <= mp_.map_bound_max_idx_(2); ++iz) {",
    "    Eigen::Vector3i id(ix, iy, iz);",
    "    if (!isInMap(id)) continue;",
    "    if (md_.occupancy_buffer_[toAddress(id)] <= mp_.min_occupancy_log_) continue;",
    "    Eigen::Vector3d p;",
    "    indexToPos(id, p);",
    "    if (!found || p(2) > z_max) {",
    "      z_max = p(2);",
    "      found = true;",
    "    }",
    "  }",
    "  if (!found) return false;",
    "  *z_out = z_max;",
    "  return true;",
    "}",
    "",
    "inline bool GridMap::queryIsTraversableStep(const Eigen::Vector3d& pos) {",
    "  if (!mp_.step_filter_enable_) return false;",
    "  Eigen::Vector3i qid;",
    "  posToIndex(pos, qid);",
    "  const double radius = mp_.step_filter_.window_radius_m;",
    "  const double radius_sq = radius * radius;",
    "  const int r_cells = static_cast<int>(std::ceil(radius * mp_.resolution_inv_));",
    "  std::vector<StepHeightSample> samples;",
    "  for (int dx = -r_cells; dx <= r_cells; ++dx) {",
    "    for (int dy = -r_cells; dy <= r_cells; ++dy) {",
    "      const int ix = qid(0) + dx;",
    "      const int iy = qid(1) + dy;",
    "      Eigen::Vector3d center;",
    "      indexToPos(Eigen::Vector3i(ix, iy, qid(2)), center);",
    "      const double ddx = center(0) - pos(0);",
    "      const double ddy = center(1) - pos(1);",
    "      if (ddx * ddx + ddy * ddy > radius_sq) continue;",
    "      double z = 0.0;",
    "      if (!columnMaxOccupiedZ(ix, iy, &z)) continue;",
    "      StepHeightSample sample;",
    "      sample.ix = ix;",
    "      sample.iy = iy;",
    "      sample.z = z;",
    "      samples.push_back(sample);",
    "    }",
    "  }",
    "  StepTraversabilityParams params = mp_.step_filter_;",
    "  params.resolution_m = mp_.resolution_;",
    "  return occupancyHitIsTraversableStep(samples, params);",
    "}",
    "",
    "inline int GridMap::getInflateOccupancy(Eigen::Vector3d pos, double yaw) {",
    "  Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);",
    "  Eigen::Vector3d front = pos + mp_.double_cylinder_offset_ * heading;",
    "  Eigen::Vector3d rear = pos - mp_.double_cylinder_offset_ * heading;",
    "",
    "  int front_occ = getInflateOccupancyFromBuffer(front, md_.occupancy_buffer_inflate_);",
    "  if (front_occ == 1 && queryIsTraversableStep(front)) front_occ = 0;",
    "  if (front_occ != 0) return front_occ;",
    "",
    "  int rear_occ = getInflateOccupancyFromBuffer(rear, md_.occupancy_buffer_inflate_);",
    "  if (rear_occ == 1 && queryIsTraversableStep(rear)) rear_occ = 0;",
    "  return rear_occ;",
    "}",
]


class PatchRefused(RuntimeError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def split_lines(data):
    parts = data.split(b"\n")
    lines = [part + b"\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def decode_line(raw):
    for ending in (b"\r\n", b"\n", b"\r"):
        if raw.endswith(ending):
            return raw[: -len(ending)].decode("utf-8"), ending
    return raw.decode("utf-8"), b""


def insert_after(lines, match, new_texts):
    for index, raw in enumerate(lines):
        text, ending = decode_line(raw)
        if text != match:
            continue
        inserted = [item.encode("utf-8") + ending for item in new_texts]
        return lines[: index + 1] + inserted + lines[index + 1 :]
    raise PatchRefused("anchor not found: %r" % match)


def replace_block(lines, old_texts, new_texts):
    decoded = [decode_line(raw)[0] for raw in lines]
    start = None
    for index in range(0, len(decoded) - len(old_texts) + 1):
        if decoded[index : index + len(old_texts)] == old_texts:
            start = index
            break
    if start is None:
        raise PatchRefused("block not found: %r" % old_texts[0])
    ending = decode_line(lines[start])[1]
    if ending == b"":
        ending = b"\n"
    rebuilt = [item.encode("utf-8") + ending for item in new_texts]
    return lines[:start] + rebuilt + lines[start + len(old_texts) :]


def write_lines(path, lines):
    path.write_bytes(b"".join(lines))


def refuse_if_immutable_build(build_dir):
    resolved = Path(build_dir).resolve()
    for name in sorted(IMMUTABLE_BUILDS):
        recorded = (HERE / "builds" / name).resolve()
        if resolved == recorded:
            raise PatchRefused("recorded builds are immutable: " + name)


def apply_patch(build_dir, now=None):
    build_dir = Path(build_dir).resolve()
    refuse_if_immutable_build(build_dir)
    header_dst = build_dir / HEADER_DST_REL
    grid_h = build_dir / GRID_H_REL
    grid_cpp = build_dir / GRID_CPP_REL
    manifest_path = build_dir / MANIFEST_NAME
    if manifest_path.exists():
        raise PatchRefused("patch manifest already exists: %s" % manifest_path)
    if header_dst.exists():
        raise PatchRefused("step header already present: %s" % header_dst)
    if not HEADER_SRC.is_file():
        raise PatchRefused("missing %s" % HEADER_SRC)
    if not grid_h.is_file() or not grid_cpp.is_file():
        raise PatchRefused("plan_env sources missing under %s" % build_dir)

    h_bytes = grid_h.read_bytes()
    cpp_bytes = grid_cpp.read_bytes()
    h_sha = sha256_bytes(h_bytes)
    cpp_sha = sha256_bytes(cpp_bytes)
    if h_sha != SCAN_04_GRID_H_SHA256:
        raise PatchRefused("grid_map.h hash mismatch: %s != %s" % (h_sha, SCAN_04_GRID_H_SHA256))
    if cpp_sha != SCAN_04_GRID_CPP_SHA256:
        raise PatchRefused("grid_map.cpp hash mismatch: %s != %s" % (cpp_sha, SCAN_04_GRID_CPP_SHA256))

    h_lines = split_lines(h_bytes)
    if INCLUDE_LINE in [decode_line(raw)[0] for raw in h_lines]:
        raise PatchRefused("include already present")
    h_lines = insert_after(h_lines, INCLUDE_ANCHOR, [INCLUDE_LINE])
    h_lines = insert_after(h_lines, PARAM_ANCHOR, PARAM_INSERT)
    h_lines = insert_after(h_lines, DECL_ANCHOR, DECL_INSERT)
    h_lines = replace_block(h_lines, OLD_INFLATE, NEW_INFLATE)

    cpp_lines = split_lines(cpp_bytes)
    cpp_decoded = [decode_line(raw)[0] for raw in cpp_lines]
    frozen_loads = (
        '  load_parameter(node_, "grid_map.ground_height", mp_.ground_height_, 0.0);',
        '  load_parameter(node_, "grid_map.vis_height", mp_.vis_height_, 0.3);',
        '  load_parameter(node_, "grid_map.cloud_is_world", mp_.cloud_is_world_, true);',
    )
    for frozen in frozen_loads:
        if frozen not in cpp_decoded:
            raise PatchRefused("frozen occupancy load missing before patch: %s" % frozen)
    cpp_lines = insert_after(cpp_lines, CPP_ANCHOR, CPP_INSERT)
    cpp_decoded_after = [decode_line(raw)[0] for raw in cpp_lines]
    for frozen in frozen_loads:
        if frozen not in cpp_decoded_after:
            raise PatchRefused("frozen occupancy load missing after patch: %s" % frozen)

    header_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HEADER_SRC, header_dst)
    write_lines(grid_h, h_lines)
    write_lines(grid_cpp, cpp_lines)

    patched_h = grid_h.read_text(encoding="utf-8", errors="replace")
    if "if (front_occ == 1 && queryIsTraversableStep(front))" not in patched_h:
        raise PatchRefused("inflate hook missing after write")

    manifest = {
        "schema_version": 1,
        "purpose": "Global ETH-style step rule in SCAN getInflateOccupancy",
        "build_dir": str(build_dir),
        "header_src": str(HEADER_SRC),
        "header_src_sha256": sha256_bytes(HEADER_SRC.read_bytes()),
        "grid_map_h_before_sha256": h_sha,
        "grid_map_cpp_before_sha256": cpp_sha,
        "grid_map_h_after_sha256": sha256_bytes(grid_h.read_bytes()),
        "grid_map_cpp_after_sha256": sha256_bytes(grid_cpp.read_bytes()),
        "applied_utc": (now or datetime.now(timezone.utc)).isoformat(),
        "unchanged": "ground_height, vis_height, cloud_is_world load lines; planner.yaml not touched",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_name", help="Directory name under p2b_execution/builds")
    args = parser.parse_args(argv)
    if not args.build_name.replace("_", "").isalnum():
        raise ValueError("Invalid build name")
    if args.build_name in IMMUTABLE_BUILDS:
        raise PatchRefused("recorded builds are immutable: " + args.build_name)
    manifest = apply_patch(HERE / "builds" / args.build_name)
    print(json.dumps({"ok": True, "manifest": str(HERE / "builds" / args.build_name / MANIFEST_NAME),
                      "h_after": manifest["grid_map_h_after_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
