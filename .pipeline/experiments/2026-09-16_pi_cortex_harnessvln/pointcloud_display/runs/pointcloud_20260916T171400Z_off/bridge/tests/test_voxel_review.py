import json
from pathlib import Path
from types import SimpleNamespace
import struct
import tempfile

import numpy as np
import pytest

from lite3_sim_bridge.voxel_review import (
    pointcloud2_xyz,
    render_voxel_review,
    transform_sensor_points,
)


def _field(name, offset, datatype=7, count=1):
    return SimpleNamespace(name=name, offset=offset, datatype=datatype, count=count)


def _cloud(points, *, bigendian=False, row_padding=0):
    prefix = ">" if bigendian else "<"
    point_step = 16
    rows = []
    for row in points:
        payload = b"".join(
            struct.pack(prefix + "ffff", point[0], point[1], point[2], 1.0)
            for point in row
        )
        rows.append(payload + b"\x00" * row_padding)
    stamp = SimpleNamespace(sec=3, nanosec=4)
    return SimpleNamespace(
        width=len(points[0]),
        height=len(points),
        point_step=point_step,
        row_step=len(points[0]) * point_step + row_padding,
        fields=[_field("x", 0), _field("y", 4), _field("z", 8)],
        is_bigendian=bigendian,
        data=b"".join(rows),
        header=SimpleNamespace(stamp=stamp),
    )


def test_pointcloud2_xyz_honors_fields_endianness_and_row_padding():
    message = _cloud(
        [[(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)], [(7.0, 8.0, 9.0), (10, 11, 12)]],
        bigendian=True,
        row_padding=8,
    )

    decoded = pointcloud2_xyz(message)

    np.testing.assert_allclose(
        decoded,
        np.asarray(
            [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)],
            dtype=np.float32,
        ),
    )


def test_pointcloud2_xyz_rejects_malformed_contract():
    message = _cloud([[(1.0, 2.0, 3.0)]])
    message.fields = [_field("x", 0), _field("y", 4)]
    with pytest.raises(ValueError, match="lacks XYZ"):
        pointcloud2_xyz(message)


def test_transform_sensor_points_applies_normalized_pose():
    points = np.asarray([(1.0, 0.0, 0.0)], dtype=np.float32)
    half = np.sqrt(0.5)
    transformed = transform_sensor_points(
        points,
        np.asarray((10.0, 20.0, 30.0)),
        np.asarray((0.0, 0.0, half * 2.0, half * 2.0)),
    )
    np.testing.assert_allclose(transformed, [(10.0, 21.0, 30.0)], atol=1.0e-6)
    message = _cloud([[(1.0, 2.0, 3.0)]])
    message.data = b"short"
    with pytest.raises(ValueError, match="shorter"):
        pointcloud2_xyz(message)


def test_render_voxel_review_produces_hashed_native_topic_video():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        snapshots = root / "snapshots"
        snapshots.mkdir()
        metadata_rows = []
        bbox = np.asarray(
            [
                (-2.0, -2.0, 0.0),
                (2.0, -2.0, 0.0),
                (2.0, 2.0, 2.0),
                (-2.0, 2.0, 2.0),
            ],
            dtype=np.float32,
        )
        for index in range(4):
            raw = np.asarray(
                [
                    (-0.5 + 0.1 * index, -0.3, 0.2),
                    (0.2, 0.4, 0.5),
                    (0.8, 0.7, 0.8),
                ],
                dtype=np.float32,
            )
            inflated = np.vstack((raw, raw + np.asarray((0.1, 0.0, 0.0))))
            name = f"frame_{index:06d}.npz"
            np.savez(
                snapshots / name,
                live_points=raw + np.asarray((0.0, 0.0, 0.1)),
                raw_points=raw,
                inflated_points=inflated,
                body_position=np.asarray((-1.0 + index * 0.2, 0.0, 0.4)),
                body_yaw_rad=np.asarray(0.0),
                bbox_points=bbox,
                plan_points=np.asarray(
                    [(-1.0, 0.0, 0.4), (0.0, 0.3, 0.4), (1.0, 0.0, 0.4)]
                ),
                trajectory_id=np.asarray(2),
                body_stamp_ns=np.asarray(index * 250_000_000),
                raw_stamp_ns=np.asarray(index),
                inflated_stamp_ns=np.asarray(index),
            )
            metadata_rows.append(
                {
                    "frame_index": index,
                    "snapshot_file": name,
                    "body_stamp_ns": index * 250_000_000,
                    "raw_point_count": len(raw),
                    "live_point_count": len(raw),
                    "inflated_point_count": len(inflated),
                    "body_position": [-1.0 + index * 0.2, 0.0, 0.4],
                }
            )
        metadata_path = root / "frames.jsonl"
        metadata_path.write_text(
            "".join(json.dumps(row) + "\n" for row in metadata_rows),
            encoding="utf-8",
        )
        summary_path = root / "summary.json"
        summary_path.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
        identity_path = root / "identity.json"
        identity_path.write_text(
            json.dumps(
                {
                    "forest_scene": {
                        "navigation": {"goal_world_m": [1.0, 0.0, 0.4]}
                    }
                }
            ),
            encoding="utf-8",
        )
        output = root / "voxel.mp4"
        sidecar = root / "voxel.json"

        result = render_voxel_review(
            snapshots,
            metadata_path,
            summary_path,
            identity_path,
            output,
            sidecar,
            fps=10.0,
            frame_size=(640, 360),
        )

        assert output.is_file() and output.stat().st_size > 0
        assert sidecar.is_file()
        assert result["output"]["source_snapshot_count"] == 4
        assert result["output"]["frame_count"] == 8
        assert result["sources"]["topics"][:2] == [
            "/grid_map/occupancy",
            "/grid_map/occupancy_inflate",
        ]
        assert result["render_geometry"] == {
            "spatial_dimensions": ["x", "y", "z"],
            "dimension_count": 3,
            "projection": "matplotlib_mplot3d_perspective",
            "camera": "sliding-map-following fixed RViz-style isometric view",
            "vertical_scale": 1.0,
            "raw_display_point_limit": 50_000,
            "inflated_display_point_limit": 30_000,
            "live_display_point_limit": 18_000,
            "display_sampling": "live and raw local layers complete; deterministic inflation subsampling only",
            "xy_inset_role": "auxiliary planning correlation only",
        }
        assert result["trajectory_ids"] == [2]
