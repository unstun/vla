"""Fail-closed live-cloud and transfer-video evidence for Office R2.0.1."""

from __future__ import annotations

import argparse
import fractions
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
import yaml


LIVE_CLOUD_TOPIC = "/quad_0/cloud_raw"
LIVE_CLOUD_DISPLAY = "Live LiDAR Cloud"
LIVE_CLOUD_RGB = (80, 225, 255)
RVIZ_FOXY_DECAY_SOURCE = (
    "https://github.com/ros2/rviz/blob/foxy/rviz_default_plugins/src/"
    "rviz_default_plugins/displays/pointcloud/point_cloud_common.cpp"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number} must be a JSON object")
            rows.append(row)
    if not rows:
        raise ValueError(f"JSONL input is empty: {path}")
    return rows


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"evidence output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * float(percentile)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def gap_statistics_seconds(values_ns: Sequence[int]) -> dict[str, float | None]:
    seconds = [float(value) / 1.0e9 for value in values_ns]
    return {
        "min_seconds": min(seconds) if seconds else None,
        "median_seconds": statistics.median(seconds) if seconds else None,
        "p95_seconds": _percentile(seconds, 0.95),
        "max_seconds": max(seconds) if seconds else None,
    }


def _find_named_mapping(value: Any, name: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("Name") == name:
            return value
        for child in value.values():
            match = _find_named_mapping(child, name)
            if match is not None:
                return match
    elif isinstance(value, list):
        for child in value:
            match = _find_named_mapping(child, name)
            if match is not None:
                return match
    return None


def load_live_cloud_display_contract(rviz_config_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(rviz_config_path).read_text(encoding="utf-8"))
    display = _find_named_mapping(payload, LIVE_CLOUD_DISPLAY)
    if display is None:
        raise ValueError(f"RViz display not found: {LIVE_CLOUD_DISPLAY}")
    topic = display.get("Topic")
    topic_value = topic.get("Value") if isinstance(topic, dict) else None
    decay_seconds = float(display.get("Decay Time", math.nan))
    return {
        "display_name": LIVE_CLOUD_DISPLAY,
        "class": display.get("Class"),
        "source_topic": topic_value,
        "decay_time_seconds": decay_seconds,
        "retains_latest_until_replaced": decay_seconds == 0.0,
        "official_semantics": "0 means only show the latest points",
        "official_source": RVIZ_FOXY_DECAY_SOURCE,
    }


def expected_display_visibility(
    arrival_seconds: Sequence[float],
    frame_seconds: Sequence[float],
    decay_seconds: float,
) -> list[bool]:
    """Model RViz's latest-only zero decay versus positive timed expiration."""

    arrivals = sorted(float(value) for value in arrival_seconds)
    if decay_seconds < 0.0 or not math.isfinite(decay_seconds):
        raise ValueError("decay_seconds must be finite and nonnegative")
    result: list[bool] = []
    arrival_index = -1
    for frame_time in frame_seconds:
        checked_time = float(frame_time)
        while (
            arrival_index + 1 < len(arrivals)
            and arrivals[arrival_index + 1] <= checked_time
        ):
            arrival_index += 1
        if arrival_index < 0:
            result.append(False)
        elif decay_seconds == 0.0:
            result.append(True)
        else:
            result.append(checked_time - arrivals[arrival_index] <= decay_seconds)
    return result


def summarize_visibility(visible_flags: Sequence[bool]) -> dict[str, Any]:
    flags = [bool(value) for value in visible_flags]
    if not flags or not any(flags):
        return {
            "video_frame_count": len(flags),
            "cloud_visible_frame_count": 0,
            "warmup_frame_count": len(flags),
            "post_warmup_frame_count": 0,
            "post_warmup_cloud_visible_frame_count": 0,
            "post_warmup_visible_fraction": 0.0,
            "longest_consecutive_invisible_frames": len(flags),
        }
    first_visible = flags.index(True)
    post_warmup = flags[first_visible:]
    longest_blank = 0
    current_blank = 0
    for visible in post_warmup:
        current_blank = 0 if visible else current_blank + 1
        longest_blank = max(longest_blank, current_blank)
    visible_count = sum(post_warmup)
    return {
        "video_frame_count": len(flags),
        "cloud_visible_frame_count": sum(flags),
        "warmup_frame_count": first_visible,
        "post_warmup_frame_count": len(post_warmup),
        "post_warmup_cloud_visible_frame_count": visible_count,
        "post_warmup_visible_fraction": visible_count / len(post_warmup),
        "longest_consecutive_invisible_frames": longest_blank,
    }


def classify_live_cloud_video(
    video_path: Path,
    *,
    right_half: bool = False,
    color_distance: float = 90.0,
    minimum_pixel_fraction: float = 0.008,
) -> tuple[list[bool], list[float]]:
    """Classify genuine cyan live-cloud visibility in each decoded frame."""

    import cv2

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"cannot decode live-cloud review video: {video_path}")
    target_bgr = np.asarray(LIVE_CLOUD_RGB[::-1], dtype=np.int16)
    distance_squared = float(color_distance) ** 2
    flags: list[bool] = []
    fractions: list[float] = []
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame is None or frame.size == 0:
                raise ValueError("decoded an empty live-cloud review frame")
            if right_half:
                frame = frame[:, frame.shape[1] // 2 :]
            difference = frame.astype(np.int16) - target_bgr
            squared = np.sum(difference.astype(np.int32) ** 2, axis=2)
            pixel_fraction = float(np.mean(squared <= distance_squared))
            fractions.append(pixel_fraction)
            flags.append(pixel_fraction >= minimum_pixel_fraction)
    finally:
        capture.release()
    if not flags:
        raise ValueError(f"video contains no decoded frames: {video_path}")
    return flags, fractions


def build_live_pointcloud_continuity_audit(
    generated_rows: Sequence[Mapping[str, Any]],
    native_audit: Mapping[str, Any],
    display_contract: Mapping[str, Any],
    visible_flags: Sequence[bool],
    *,
    video_pixel_fractions: Sequence[float] | None = None,
) -> dict[str, Any]:
    generated_stamps = [int(row["scan_reference_timestamp_ns"]) for row in generated_rows]
    generated_point_counts = [int(row["point_count"]) for row in generated_rows]
    generated_gaps = [
        right - left for left, right in zip(generated_stamps, generated_stamps[1:])
    ]
    observations = native_audit.get("live_lidar_observations")
    if not isinstance(observations, list):
        raise ValueError("native audit lacks live_lidar_observations")
    received_stamps = [int(row["stamp_ns"]) for row in observations]
    received_points = [int(row["point_count"]) for row in observations]
    wall_times = [int(row["wall_time_ns"]) for row in observations]
    simulator_gaps = [
        right - left for left, right in zip(received_stamps, received_stamps[1:])
        if right > left
    ]
    wall_gaps = [right - left for left, right in zip(wall_times, wall_times[1:])]
    stamp_regressions = sum(
        right <= left for left, right in zip(received_stamps, received_stamps[1:])
    )
    generated_gap_stats = gap_statistics_seconds(generated_gaps)
    simulator_gap_stats = gap_statistics_seconds(simulator_gaps)
    wall_gap_stats = gap_statistics_seconds(wall_gaps)
    generated_frequency_hz = (
        1.0 / float(generated_gap_stats["median_seconds"])
        if generated_gap_stats["median_seconds"]
        else 0.0
    )
    coverage = len(observations) / len(generated_rows) if generated_rows else 0.0
    visibility = summarize_visibility(visible_flags)
    checks = {
        "generated_scan_count_nonzero": len(generated_rows) > 0,
        "generated_scan_frequency_about_10_hz": 9.5 <= generated_frequency_hz <= 10.5,
        "generated_clouds_nonempty": bool(generated_point_counts)
        and min(generated_point_counts) > 0,
        "received_generated_coverage_at_least_0_95": coverage >= 0.95,
        "all_received_clouds_nonempty": bool(received_points)
        and min(received_points) > 0,
        "stamp_regression_count_zero": stamp_regressions == 0,
        "simulator_time_max_gap_at_most_0_2_seconds": (
            simulator_gap_stats["max_seconds"] is not None
            and float(simulator_gap_stats["max_seconds"]) <= 0.2
        ),
        "live_lidar_audit_required": native_audit.get("require_live_lidar") is True,
        "live_lidar_publish_count_nonzero": int(
            native_audit.get("live_lidar_publish_count", 0)
        ) > 0,
        "live_lidar_received_count_nonzero": len(observations) > 0,
        "source_mode_live": native_audit.get("source_mode") == "live",
        "source_topic_is_quad_0_cloud_raw": display_contract.get("source_topic")
        == LIVE_CLOUD_TOPIC,
        "rviz_retains_latest_until_replaced": display_contract.get(
            "retains_latest_until_replaced"
        )
        is True,
        "post_warmup_cloud_visible_fraction_at_least_0_98": visibility[
            "post_warmup_visible_fraction"
        ]
        >= 0.98,
        "longest_invisible_run_at_most_two_frames": visibility[
            "longest_consecutive_invisible_frames"
        ]
        <= 2,
    }
    point_stats = {
        "minimum": min(received_points) if received_points else None,
        "median": statistics.median(received_points) if received_points else None,
        "maximum": max(received_points) if received_points else None,
    }
    return {
        "schema_version": 1,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "claim_boundary": (
            "Same-run observation-only live /quad_0/cloud_raw continuity and delivered-video "
            "visibility audit for one Office R2.0.1 short preflight; no cloud is "
            "republished, replayed, synthesized, or post-rendered, and this does not "
            "satisfy AC54 or AC55."
        ),
        "source_topic": LIVE_CLOUD_TOPIC,
        "source_mode": native_audit.get("source_mode"),
        "generated_scan_count": len(generated_rows),
        "generated_scan_frequency_hz": generated_frequency_hz,
        "generated_simulator_time_gap": generated_gap_stats,
        "ros_received_message_count": len(observations),
        "nonempty_message_count": sum(value > 0 for value in received_points),
        "first_ros_stamp_ns": received_stamps[0] if received_stamps else None,
        "last_ros_stamp_ns": received_stamps[-1] if received_stamps else None,
        "stamp_regression_count": stamp_regressions,
        "simulator_time_gap": simulator_gap_stats,
        "wall_time_arrival_gap": wall_gap_stats,
        "wall_time_gate_policy": "record_only_not_a_sensor_frequency_gate",
        "generated_received_coverage": coverage,
        "point_count": point_stats,
        "require_live_lidar": native_audit.get("require_live_lidar"),
        "live_lidar_publish_count": native_audit.get("live_lidar_publish_count", 0),
        "rviz_display_contract": dict(display_contract),
        "video_visibility": {
            **visibility,
            "cyan_rgb": list(LIVE_CLOUD_RGB),
            "color_distance": 90.0,
            "minimum_pixel_fraction": 0.008,
            "per_frame_pixel_fraction": list(video_pixel_fractions or []),
        },
        "startup_end_coverage_note": (
            "Coverage uses total same-run generated and received counts; a small difference "
            "is permitted only at observer startup or shutdown and remains visible here."
        ),
        "checks": checks,
    }


def probe_video(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe is required")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,profile,width,height,pix_fmt,r_frame_rate,nb_frames,nb_read_frames,color_range,color_space,color_transfer,color_primaries",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    if len(streams) != 1:
        raise ValueError(f"expected one video stream: {path}")
    stream = streams[0]
    fmt = payload.get("format") or {}
    rate = str(stream.get("r_frame_rate", "0/0"))
    frame_count_value = stream.get("nb_read_frames") or stream.get("nb_frames") or 0
    return {
        "codec_name": stream.get("codec_name"),
        "profile": stream.get("profile"),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "pix_fmt": stream.get("pix_fmt"),
        "r_frame_rate": rate,
        "fps": float(fractions.Fraction(rate)),
        "frame_count": int(frame_count_value),
        "duration_seconds": float(fmt.get("duration", 0.0)),
        "size_bytes": int(fmt.get("size", Path(path).stat().st_size)),
        "color_range": stream.get("color_range"),
        "color_space": stream.get("color_space"),
        "color_transfer": stream.get("color_transfer"),
        "color_primaries": stream.get("color_primaries"),
    }


def decode_video_frame_count(path: Path) -> int:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required")
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-xerror",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-f",
            "framemd5",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"full decode failed for {path}: {result.stderr.strip()}")
    return sum(
        1 for line in result.stdout.splitlines() if line and not line.startswith("#")
    )


def select_smallest_passing_candidate(
    candidates: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    passing = [candidate for candidate in candidates if candidate.get("status") == "PASS"]
    if not passing:
        raise ValueError("no transfer candidate passed every quality gate")
    return min(passing, key=lambda candidate: int(candidate["probe"]["size_bytes"]))


def _measure_ssim(master_path: Path, candidate_path: Path) -> float:
    ffmpeg = shutil.which("ffmpeg")
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-i",
            str(master_path),
            "-i",
            str(candidate_path),
            "-lavfi",
            "[0:v][1:v]ssim",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"SSIM failed: {result.stderr.strip()}")
    matches = re.findall(r"All:([0-9.]+)", result.stderr)
    if not matches:
        raise ValueError("ffmpeg SSIM output did not contain All score")
    return float(matches[-1])


def _measure_vmaf_if_available(master_path: Path, candidate_path: Path) -> dict[str, Any]:
    ffmpeg = shutil.which("ffmpeg")
    filters = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-filters"], capture_output=True, text=True
    )
    if "libvmaf" not in filters.stdout:
        return {"available": False, "score": None, "reason": "libvmaf filter unavailable"}
    with tempfile.TemporaryDirectory() as directory:
        log_path = Path(directory) / "vmaf.json"
        result = subprocess.run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-i",
                str(candidate_path),
                "-i",
                str(master_path),
                "-lavfi",
                f"[0:v][1:v]libvmaf=log_fmt=json:log_path={log_path}",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not log_path.is_file():
            return {"available": True, "score": None, "reason": result.stderr.strip()}
        payload = json.loads(log_path.read_text(encoding="utf-8"))
        score = payload.get("pooled_metrics", {}).get("vmaf", {}).get("mean")
        return {"available": True, "score": score, "reason": None}


def build_transfer_candidate_validation(
    master_probe: Mapping[str, Any],
    candidate_probe: Mapping[str, Any],
    *,
    decoded_frame_count: int,
    ssim: float,
    minimum_ssim: float = 0.97,
) -> dict[str, Any]:
    reduction = 1.0 - (
        int(candidate_probe["size_bytes"]) / int(master_probe["size_bytes"])
    )
    checks = {
        "resolution_3840x1080": [candidate_probe["width"], candidate_probe["height"]]
        == [3840, 1080],
        "frame_rate_25fps": candidate_probe["r_frame_rate"] == "25/1",
        "frame_count_matches_master": candidate_probe["frame_count"]
        == master_probe["frame_count"],
        "duration_matches_master": abs(
            float(candidate_probe["duration_seconds"])
            - float(master_probe["duration_seconds"])
        )
        <= 1.0 / 25.0,
        "h264_high": candidate_probe["codec_name"] == "h264"
        and candidate_probe["profile"] == "High",
        "yuv420p": candidate_probe["pix_fmt"] == "yuv420p",
        "bt709": candidate_probe["color_space"] == "bt709"
        and candidate_probe["color_transfer"] == "bt709"
        and candidate_probe["color_primaries"] == "bt709",
        "full_decode_matches_master": decoded_frame_count == master_probe["frame_count"],
        "size_reduction_at_least_0_50": reduction >= 0.50,
        "ssim_at_least_minimum": float(ssim) >= float(minimum_ssim),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "size_reduction_fraction": reduction,
        "ssim": ssim,
        "minimum_ssim": minimum_ssim,
    }


def compress_transfer_video(
    master_path: Path,
    transfer_path: Path,
    ffprobe_output_path: Path,
    validation_output_path: Path,
    sha256_output_path: Path,
    manifest_output_path: Path,
) -> dict[str, Any]:
    paths = [
        transfer_path,
        ffprobe_output_path,
        validation_output_path,
        sha256_output_path,
        manifest_output_path,
    ]
    if not Path(master_path).is_file() or Path(master_path).is_symlink():
        raise ValueError("master video must be an existing regular file")
    for path in paths:
        if Path(path).exists() or Path(path).is_symlink():
            raise FileExistsError(f"transfer output already exists: {path}")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None or shutil.which("ffprobe") is None:
        raise RuntimeError("ffmpeg and ffprobe are required")
    master_hash_before = sha256_file(master_path)
    master_probe = probe_video(master_path)
    ffmpeg_version = subprocess.run(
        [ffmpeg, "-version"], capture_output=True, text=True, check=True
    ).stdout.splitlines()[0]
    encoder_version = subprocess.run(
        [ffmpeg, "-hide_banner", "-h", "encoder=libx264"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()[0]
    candidate_records: list[dict[str, Any]] = []
    candidate_paths: list[Path] = []
    for crf in (22, 24, 26):
        candidate_path = Path(transfer_path).with_name(
            f"{Path(transfer_path).stem}_crf{crf}{Path(transfer_path).suffix}"
        )
        if candidate_path.exists() or candidate_path.is_symlink():
            raise FileExistsError(f"CRF candidate already exists: {candidate_path}")
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-n",
            "-i",
            str(master_path),
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            str(crf),
            "-profile:v",
            "high",
            "-pix_fmt",
            "yuv420p",
            "-color_range",
            "tv",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            "-r",
            "25",
            "-movflags",
            "+faststart",
            str(candidate_path),
        ]
        subprocess.run(command, check=True)
        candidate_paths.append(candidate_path)
        candidate_probe = probe_video(candidate_path)
        decoded_count = decode_video_frame_count(candidate_path)
        ssim = _measure_ssim(master_path, candidate_path)
        validation = build_transfer_candidate_validation(
            master_probe,
            candidate_probe,
            decoded_frame_count=decoded_count,
            ssim=ssim,
        )
        candidate_records.append(
            {
                "crf": crf,
                "path": str(candidate_path),
                "command": command,
                "probe": candidate_probe,
                "decoded_frame_count": decoded_count,
                "ssim": ssim,
                "status": validation["status"],
                "validation": validation,
            }
        )
    selected = select_smallest_passing_candidate(candidate_records)
    selected_path = Path(str(selected["path"]))
    selected_path.replace(transfer_path)
    for candidate_path in candidate_paths:
        if candidate_path != selected_path and candidate_path.exists():
            candidate_path.unlink()
    transfer_probe = probe_video(transfer_path)
    transfer_decode_count = decode_video_frame_count(transfer_path)
    transfer_ssim = _measure_ssim(master_path, transfer_path)
    transfer_validation = build_transfer_candidate_validation(
        master_probe,
        transfer_probe,
        decoded_frame_count=transfer_decode_count,
        ssim=transfer_ssim,
    )
    transfer_validation["layout"] = {
        "left": "high external side third-person view",
        "right": "same-run native 5070 Ti RViz synchronized to simulator time",
    }
    transfer_validation["vmaf"] = _measure_vmaf_if_available(
        master_path, transfer_path
    )
    transfer_validation["manual_review"] = "pending direct contact-sheet and video inspection"
    if sha256_file(master_path) != master_hash_before:
        raise ValueError("master video changed during transfer encoding")
    transfer_hash = sha256_file(transfer_path)
    Path(ffprobe_output_path).write_text(
        json.dumps({"streams": [transfer_probe], "format": {
            "duration": transfer_probe["duration_seconds"],
            "size": transfer_probe["size_bytes"],
        }}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    Path(validation_output_path).write_text(
        json.dumps(transfer_validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    Path(sha256_output_path).write_text(
        f"{master_hash_before}  {Path(master_path).name}\n"
        f"{transfer_hash}  {Path(transfer_path).name}\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "status": transfer_validation["status"],
        "claim_boundary": (
            "Verified transfer packaging for the unchanged Office dual-view master; "
            "compression does not alter navigation evidence or satisfy AC54/AC55."
        ),
        "master_path": str(master_path),
        "transfer_path": str(transfer_path),
        "master_sha256": master_hash_before,
        "transfer_sha256": transfer_hash,
        "master_size_bytes": master_probe["size_bytes"],
        "transfer_size_bytes": transfer_probe["size_bytes"],
        "size_reduction_fraction": transfer_validation["size_reduction_fraction"],
        "ffmpeg_version": ffmpeg_version,
        "encoder_version": encoder_version,
        "candidates": candidate_records,
        "selected_crf": selected["crf"],
        "selection_reason": "smallest CRF 22/24/26 candidate passing media, full-decode, size, and SSIM gates",
        "master_probe": master_probe,
        "transfer_probe": transfer_probe,
        "transfer_validation": transfer_validation,
        "remote_local_hash_match": None,
    }
    Path(manifest_output_path).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if transfer_validation["status"] != "PASS":
        raise ValueError("selected transfer video failed final validation")
    return manifest


def _audit_command(args: argparse.Namespace) -> int:
    generated_rows = _read_jsonl(args.sensor_metrics)
    native_audit = json.loads(args.native_audit.read_text(encoding="utf-8"))
    display_contract = load_live_cloud_display_contract(args.rviz_config)
    visible_flags, fractions_per_frame = classify_live_cloud_video(
        args.video, right_half=args.right_half
    )
    payload = build_live_pointcloud_continuity_audit(
        generated_rows,
        native_audit,
        display_contract,
        visible_flags,
        video_pixel_fractions=fractions_per_frame,
    )
    _write_json_exclusive(args.output, payload)
    if payload["status"] != "PASS":
        raise SystemExit("live point-cloud continuity audit failed")
    return 0


def _compress_command(args: argparse.Namespace) -> int:
    compress_transfer_video(
        args.master,
        args.transfer,
        args.ffprobe_output,
        args.validation_output,
        args.sha256_output,
        args.manifest_output,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit")
    audit.add_argument("--sensor-metrics", type=Path, required=True)
    audit.add_argument("--native-audit", type=Path, required=True)
    audit.add_argument("--rviz-config", type=Path, required=True)
    audit.add_argument("--video", type=Path, required=True)
    audit.add_argument("--right-half", action="store_true")
    audit.add_argument("--output", type=Path, required=True)
    audit.set_defaults(handler=_audit_command)
    compress = subparsers.add_parser("compress")
    compress.add_argument("--master", type=Path, required=True)
    compress.add_argument("--transfer", type=Path, required=True)
    compress.add_argument("--ffprobe-output", type=Path, required=True)
    compress.add_argument("--validation-output", type=Path, required=True)
    compress.add_argument("--sha256-output", type=Path, required=True)
    compress.add_argument("--manifest-output", type=Path, required=True)
    compress.set_defaults(handler=_compress_command)
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
