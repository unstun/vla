"""Preflight visual verification for Isaac Sim Office L0 RGB camera capture."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional


def probe_video_stream(video_path: Path) -> Dict[str, Any]:
    """Inspect video file metadata using ffprobe."""
    if not video_path.is_file():
        raise FileNotFoundError(f"video not found: {video_path}")
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size,bit_rate:stream=codec_name,width,height,nb_frames,r_frame_rate",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    payload = json.loads(res.stdout)
    streams = payload.get("streams", [])
    if not streams:
        raise ValueError(f"no video streams found in {video_path}")
    v_stream = streams[0]
    format_info = payload.get("format", {})

    r_fps = v_stream.get("r_frame_rate", "0/1")
    num, den = map(int, r_fps.split("/")) if "/" in r_fps else (int(r_fps), 1)
    fps = num / den if den > 0 else 0.0

    nb_frames = int(v_stream.get("nb_frames", 0))
    duration = float(format_info.get("duration", 0.0))

    return {
        "codec": v_stream.get("codec_name"),
        "width": int(v_stream.get("width", 0)),
        "height": int(v_stream.get("height", 0)),
        "fps": fps,
        "nb_frames": nb_frames,
        "duration_seconds": duration,
        "size_bytes": int(format_info.get("size", 0)),
    }


def extract_and_analyze_frames(
    video_path: Path,
    num_samples: int = 10,
    min_luma_mean: float = 25.0,
    max_luma_mean: float = 230.0,
    min_luma_std: float = 12.0,
    min_temporal_diff: float = 1.0,
) -> Dict[str, Any]:
    """Extract sample frames and compute spatial and temporal luma statistics."""
    meta = probe_video_stream(video_path)
    total_frames = meta["nb_frames"]
    if total_frames < 2:
        raise ValueError(f"insufficient frames in video ({total_frames})")

    step = max(1, total_frames // (num_samples + 1))
    sample_indices = [min(total_frames - 1, step * i) for i in range(1, num_samples + 1)]
    sample_indices = sorted(set(sample_indices))

    # Extract frames using ffmpeg
    import tempfile
    import numpy as np
    from PIL import Image

    frame_stats: List[Dict[str, Any]] = []
    luma_arrays: List[np.ndarray] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for idx in sample_indices:
            out_img = tmp_path / f"frame_{idx:05d}.png"
            cmd = [
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-vf", f"select=eq(n\\,{idx})",
                "-vframes", "1",
                str(out_img),
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            if not out_img.is_file():
                continue
            img = Image.open(out_img)
            arr = np.array(img, dtype=np.float32)
            if arr.ndim != 3 or arr.shape[2] < 3:
                continue
            # ITU-R BT.601 luma
            luma = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
            luma_arrays.append(luma)
            f_mean = float(luma.mean())
            f_std = float(luma.std())
            f_min = float(luma.min())
            f_max = float(luma.max())
            passed = (min_luma_mean <= f_mean <= max_luma_mean) and (f_std >= min_luma_std)
            frame_stats.append({
                "frame_index": idx,
                "luma_mean": f_mean,
                "luma_std": f_std,
                "luma_min": f_min,
                "luma_max": f_max,
                "passed_spatial_contrast": passed,
            })

    # Temporal differences between consecutive samples
    temporal_diffs: List[float] = []
    for i in range(len(luma_arrays) - 1):
        diff = float(np.mean(np.abs(luma_arrays[i+1] - luma_arrays[i])))
        temporal_diffs.append(diff)

    mean_temporal_diff = float(np.mean(temporal_diffs)) if temporal_diffs else 0.0
    nonblank_count = sum(1 for f in frame_stats if f["passed_spatial_contrast"])
    nonblank_fraction = nonblank_count / len(frame_stats) if frame_stats else 0.0

    all_passed = (
        nonblank_fraction >= 0.95
        and mean_temporal_diff >= min_temporal_diff
        and meta["width"] >= 640
        and meta["height"] >= 360
    )

    return {
        "status": "PASS" if all_passed else "FAIL",
        "video_metadata": meta,
        "sample_count": len(frame_stats),
        "nonblank_fraction": nonblank_fraction,
        "mean_temporal_diff": mean_temporal_diff,
        "frame_stats": frame_stats,
        "limits": {
            "min_luma_mean": min_luma_mean,
            "max_luma_mean": max_luma_mean,
            "min_luma_std": min_luma_std,
            "min_temporal_diff": min_temporal_diff,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify non-blank RGB video quality.")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = extract_and_analyze_frames(args.video)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "nonblank_fraction": report["nonblank_fraction"], "mean_temporal_diff": report["mean_temporal_diff"]}))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
