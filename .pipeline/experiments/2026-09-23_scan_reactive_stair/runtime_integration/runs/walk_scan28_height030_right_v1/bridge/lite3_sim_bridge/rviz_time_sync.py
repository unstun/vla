"""Frame-accurate simulator-time synchronization for native SCAN RViz video.

The raw RViz screen capture follows wall time because Isaac runs slower than
real time.  This module records when each immutable camera-trace row becomes
visible to the capture process, then selects the corresponding RViz frame for
every simulator-time camera frame.  It never synthesizes planner state or
replays point clouds.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import signal
import threading
import time
from typing import Any, Dict, List, Optional, Sequence


def _process_is_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def observe_camera_trace(
    camera_trace_path: Path,
    output_timeline_path: Path,
    *,
    capture_start_epoch_ns: int,
    producer_pid: int,
    poll_seconds: float = 0.005,
) -> int:
    """Record the wall-clock observation time of every appended trace row."""
    camera_trace_path = Path(camera_trace_path)
    output_timeline_path = Path(output_timeline_path)
    if output_timeline_path.exists() or output_timeline_path.is_symlink():
        raise FileExistsError(f"RViz timeline output already exists: {output_timeline_path}")
    if capture_start_epoch_ns <= 0 or producer_pid <= 0:
        raise ValueError("capture clock and producer PID must be positive")
    if not math.isfinite(float(poll_seconds)) or not 0.001 <= poll_seconds <= 0.1:
        raise ValueError("poll_seconds must be within [0.001, 0.1]")

    output_timeline_path.parent.mkdir(parents=True, exist_ok=True)
    stop_requested = False
    observer_start_epoch_ns = time.time_ns()
    observer_start_monotonic_ns = time.monotonic_ns()
    capture_start_monotonic_ns = observer_start_monotonic_ns - (
        observer_start_epoch_ns - capture_start_epoch_ns
    )

    def _stop(_signum: int, _frame: Any) -> None:
        nonlocal stop_requested
        stop_requested = True

    previous_sigterm = None
    previous_sigint = None
    if threading.current_thread() is threading.main_thread():
        previous_sigterm = signal.signal(signal.SIGTERM, _stop)
        previous_sigint = signal.signal(signal.SIGINT, _stop)
    row_count = 0
    source_handle = None
    producer_dead_since: Optional[float] = None
    try:
        with output_timeline_path.open("x", encoding="utf-8") as output_handle:
            output_handle.write(
                json.dumps(
                    {
                        "kind": "capture_clock",
                        "schema_version": 1,
                        "capture_start_epoch_ns": int(capture_start_epoch_ns),
                        "capture_start_monotonic_ns_estimate": int(
                            capture_start_monotonic_ns
                        ),
                        "poll_seconds": float(poll_seconds),
                        "clock": "CLOCK_MONOTONIC_ns",
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            output_handle.flush()
            while not stop_requested:
                if source_handle is None and camera_trace_path.is_file():
                    source_handle = camera_trace_path.open("r", encoding="utf-8")
                appended = False
                if source_handle is not None:
                    while True:
                        line_start = source_handle.tell()
                        line = source_handle.readline()
                        if not line:
                            break
                        if not line.endswith("\n"):
                            # The producer flushes after a complete JSON row,
                            # but a concurrent reader can reach EOF between the
                            # write and newline. Rewind and retry the whole row.
                            source_handle.seek(line_start)
                            break
                        if not line.strip():
                            continue
                        trace_row = json.loads(line)
                        observed_epoch_ns = time.time_ns()
                        observed_monotonic_ns = time.monotonic_ns()
                        output_handle.write(
                            json.dumps(
                                {
                                    "kind": "trace_observation",
                                    "schema_version": 1,
                                    "frame_index": int(trace_row["frame_index"]),
                                    "step": int(trace_row["step"]),
                                    "sim_time_seconds": float(
                                        trace_row["sim_time_seconds"]
                                    ),
                                    "observed_epoch_ns": observed_epoch_ns,
                                    "observed_monotonic_ns": observed_monotonic_ns,
                                    "capture_elapsed_seconds": (
                                        observed_monotonic_ns
                                        - capture_start_monotonic_ns
                                    )
                                    / 1.0e9,
                                },
                                sort_keys=True,
                            )
                            + "\n"
                        )
                        output_handle.flush()
                        row_count += 1
                        appended = True

                if _process_is_alive(producer_pid):
                    producer_dead_since = None
                elif producer_dead_since is None:
                    producer_dead_since = time.monotonic()
                elif not appended and time.monotonic() - producer_dead_since >= 1.0:
                    break
                time.sleep(poll_seconds)
    finally:
        if source_handle is not None:
            source_handle.close()
        if previous_sigterm is not None and previous_sigint is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)
            signal.signal(signal.SIGINT, previous_sigint)
    if row_count <= 0:
        raise ValueError("RViz timeline observer recorded no camera-trace rows")
    return row_count


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            rows.append(row)
    return rows


def synchronize_rviz_video(
    source_video_path: Path,
    timeline_path: Path,
    camera_trace_path: Path,
    reference_video_path: Path,
    output_video_path: Path,
    output_metadata_path: Path,
) -> Dict[str, Any]:
    """Select one captured RViz frame for every simulator-time camera frame."""
    import cv2

    from .office_review_presentation import (
        DirectH264Writer,
        _probe_video_evidence,
        frozen_quality_profile,
        sha256_file,
        write_text_exclusive,
    )

    paths = (
        source_video_path,
        timeline_path,
        camera_trace_path,
        reference_video_path,
    )
    for path in paths:
        if not Path(path).is_file() or Path(path).is_symlink():
            raise ValueError(f"required regular RViz synchronization input is missing: {path}")
    for path in (output_video_path, output_metadata_path):
        if Path(path).exists() or Path(path).is_symlink():
            raise FileExistsError(f"RViz synchronization output already exists: {path}")

    trace_rows = _read_jsonl(camera_trace_path)
    timeline_rows = _read_jsonl(timeline_path)
    if not trace_rows or not timeline_rows:
        raise ValueError("RViz synchronization inputs cannot be empty")
    clock_rows = [row for row in timeline_rows if row.get("kind") == "capture_clock"]
    observations = [
        row for row in timeline_rows if row.get("kind") == "trace_observation"
    ]
    if len(clock_rows) != 1:
        raise ValueError("RViz timeline must contain exactly one capture clock")
    if len(observations) != len(trace_rows):
        raise ValueError(
            f"RViz observations {len(observations)} != camera trace rows {len(trace_rows)}"
        )

    source_probe = _probe_video_evidence(Path(source_video_path))
    reference_probe = _probe_video_evidence(Path(reference_video_path))
    source_frame_count = source_probe["nb_read_frames"] or source_probe["nb_frames"]
    reference_frame_count = (
        reference_probe["nb_read_frames"] or reference_probe["nb_frames"]
    )
    if source_frame_count <= 0 or reference_frame_count != len(trace_rows):
        raise ValueError("source/reference frame count does not match synchronization evidence")
    reference_fps = float(reference_probe["fps"])
    source_fps = float(source_probe["fps"])
    if not reference_fps.is_integer() or reference_fps < 25.0 or source_fps <= 0.0:
        raise ValueError("RViz synchronization requires integer >=25 reference fps")

    mappings: List[Dict[str, Any]] = []
    previous_elapsed = -math.inf
    previous_source_index = -1
    for trace_row, observed in zip(trace_rows, observations, strict=True):
        for key in ("frame_index", "step"):
            if int(observed.get(key, -1)) != int(trace_row.get(key, -2)):
                raise ValueError(f"RViz timeline {key} does not match camera trace")
        if abs(
            float(observed.get("sim_time_seconds", math.nan))
            - float(trace_row.get("sim_time_seconds", math.nan))
        ) > 1.0e-9:
            raise ValueError("RViz timeline simulator time does not match camera trace")
        elapsed = float(observed.get("capture_elapsed_seconds", math.nan))
        if not math.isfinite(elapsed) or elapsed < 0.0 or elapsed <= previous_elapsed:
            raise ValueError("RViz capture elapsed time is not finite and strictly increasing")
        source_index = int(round(elapsed * source_fps))
        if source_index <= previous_source_index or source_index >= source_frame_count:
            raise ValueError("RViz source frame mapping is stale, duplicate, or out of range")
        mapped_time = source_index / source_fps
        mappings.append(
            {
                "frame_index": int(trace_row["frame_index"]),
                "step": int(trace_row["step"]),
                "sim_time_seconds": float(trace_row["sim_time_seconds"]),
                "capture_elapsed_seconds": elapsed,
                "source_rviz_frame_index": source_index,
                "source_rviz_time_seconds": mapped_time,
                "capture_quantization_error_seconds": abs(mapped_time - elapsed),
            }
        )
        previous_elapsed = elapsed
        previous_source_index = source_index

    output_profile = frozen_quality_profile()
    output_profile.update(
        {
            "resolution_width": int(source_probe["width"]),
            "resolution_height": int(source_probe["height"]),
            "crf": 14,
            "preset": "medium",
        }
    )
    writer = DirectH264Writer(
        Path(output_video_path), int(reference_fps), output_profile
    )
    capture = cv2.VideoCapture(str(source_video_path))
    if not capture.isOpened():
        writer.close()
        raise ValueError(f"cannot decode native RViz source: {source_video_path}")
    wanted = {row["source_rviz_frame_index"]: index for index, row in enumerate(mappings)}
    written = 0
    source_index = 0
    try:
        while source_index <= previous_source_index:
            ok, frame = capture.read()
            if not ok or frame is None:
                raise ValueError(
                    f"native RViz decode ended at frame {source_index} before mapping completed"
                )
            if source_index in wanted:
                writer.append_data(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                written += 1
            source_index += 1
    finally:
        capture.release()
        writer.close()
    if written != len(mappings):
        raise ValueError(f"synchronized RViz wrote {written} frames, expected {len(mappings)}")

    output_probe = _probe_video_evidence(Path(output_video_path))
    output_frame_count = output_probe["nb_read_frames"] or output_probe["nb_frames"]
    if output_frame_count != len(trace_rows) or output_probe["fps"] != reference_fps:
        raise ValueError("synchronized RViz output frame count/rate mismatch")
    metadata = {
        "schema_version": 1,
        "mode": "native_rviz_wall_clock_to_simulator_time_frame_selection",
        "claim_boundary": (
            "Each output frame is selected from the native 5070 Ti RViz screen capture "
            "at the wall-clock observation of the matching camera-trace simulator state; "
            "no point cloud, occupancy, or planned path is synthesized or replayed."
        ),
        "frame_count": len(mappings),
        "fps": reference_fps,
        "resolution": [int(output_probe["width"]), int(output_probe["height"])],
        "source_rviz_frame_count": int(source_frame_count),
        "source_rviz_fps": source_fps,
        "max_capture_quantization_error_seconds": max(
            row["capture_quantization_error_seconds"] for row in mappings
        ),
        "poll_seconds": float(clock_rows[0]["poll_seconds"]),
        "input_sha256": {
            "source_rviz_video": sha256_file(Path(source_video_path)),
            "timeline": sha256_file(Path(timeline_path)),
            "camera_trace": sha256_file(Path(camera_trace_path)),
            "reference_first_view": sha256_file(Path(reference_video_path)),
        },
        "output_sha256": sha256_file(Path(output_video_path)),
        "frame_mapping": mappings,
    }
    write_text_exclusive(
        Path(output_metadata_path), json.dumps(metadata, indent=2, sort_keys=True)
    )
    return metadata


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize native RViz to simulator time")
    subparsers = parser.add_subparsers(dest="command", required=True)

    observe = subparsers.add_parser("observe")
    observe.add_argument("--camera-trace", type=Path, required=True)
    observe.add_argument("--output-timeline", type=Path, required=True)
    observe.add_argument("--capture-start-epoch-ns", type=int, required=True)
    observe.add_argument("--producer-pid", type=int, required=True)
    observe.add_argument("--poll-seconds", type=float, default=0.005)

    synchronize = subparsers.add_parser("synchronize")
    synchronize.add_argument("--source-video", type=Path, required=True)
    synchronize.add_argument("--timeline", type=Path, required=True)
    synchronize.add_argument("--camera-trace", type=Path, required=True)
    synchronize.add_argument("--reference-video", type=Path, required=True)
    synchronize.add_argument("--output-video", type=Path, required=True)
    synchronize.add_argument("--output-metadata", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "observe":
        count = observe_camera_trace(
            args.camera_trace,
            args.output_timeline,
            capture_start_epoch_ns=args.capture_start_epoch_ns,
            producer_pid=args.producer_pid,
            poll_seconds=args.poll_seconds,
        )
        print(json.dumps({"observed_camera_trace_rows": count}, sort_keys=True))
        return 0
    metadata = synchronize_rviz_video(
        args.source_video,
        args.timeline,
        args.camera_trace,
        args.reference_video,
        args.output_video,
        args.output_metadata,
    )
    print(json.dumps({key: metadata[key] for key in ("frame_count", "fps", "resolution")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
