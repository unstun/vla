#!/usr/bin/env python3
"""Inspect the released TIC-VLA checkpoint on CPU without constructing a model."""

import argparse
import hashlib
import json
from pathlib import Path

import torch


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    checkpoint = torch.load(str(args.checkpoint), map_location="cpu")
    if not isinstance(checkpoint, dict):
        raise TypeError("checkpoint root must be a dict")
    state_dict = checkpoint.get("state_dict")
    if not isinstance(state_dict, dict) or not state_dict:
        raise ValueError("checkpoint state_dict is missing or empty")

    tensor_records = []
    non_tensor_keys = []
    for key in sorted(state_dict):
        value = state_dict[key]
        if torch.is_tensor(value):
            tensor_records.append(
                {
                    "key": key,
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                    "numel": value.numel(),
                }
            )
        else:
            non_tensor_keys.append({"key": key, "type": type(value).__name__})

    report = {
        "checkpoint_path": str(args.checkpoint),
        "checkpoint_bytes": args.checkpoint.stat().st_size,
        "checkpoint_sha256": sha256(args.checkpoint),
        "root_type": type(checkpoint).__name__,
        "root_keys": sorted(checkpoint.keys()),
        "state_dict_key_count": len(state_dict),
        "tensor_count": len(tensor_records),
        "tensor_numel": sum(item["numel"] for item in tensor_records),
        "non_tensor_state_entries": non_tensor_keys,
        "state_dict": tensor_records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in report if key != "state_dict"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
