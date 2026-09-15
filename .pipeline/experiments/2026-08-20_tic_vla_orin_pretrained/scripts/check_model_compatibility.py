#!/usr/bin/env python3
"""Compare the released checkpoint against the source-constructed CPU model."""

import argparse
import json
import time
from pathlib import Path

import torch

from ticvla.models.ticvla import TICVLA


def compare(source, target):
    source_keys = set(source)
    target_keys = set(target)
    common = source_keys & target_keys
    mismatches = []
    for key in sorted(common):
        if tuple(source[key].shape) != tuple(target[key].shape):
            mismatches.append(
                {
                    "key": key,
                    "checkpoint_shape": list(source[key].shape),
                    "model_shape": list(target[key].shape),
                }
            )
    return {
        "checkpoint_key_count": len(source_keys),
        "model_key_count": len(target_keys),
        "missing_keys": sorted(target_keys - source_keys),
        "unexpected_keys": sorted(source_keys - target_keys),
        "shape_mismatches": mismatches,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    checkpoint_start = time.perf_counter()
    checkpoint = torch.load(str(args.checkpoint), map_location="cpu")
    state_dict = checkpoint["state_dict"]
    checkpoint_load_seconds = time.perf_counter() - checkpoint_start

    direct_prefix = "model.vlm."
    nested_prefix = "model.vlm_model.vlm."
    action_prefix = "model.action_expert."
    direct = {key[len(direct_prefix):]: value for key, value in state_dict.items() if key.startswith(direct_prefix)}
    nested = {key[len(nested_prefix):]: value for key, value in state_dict.items() if key.startswith(nested_prefix)}
    action = {key[len(action_prefix):]: value for key, value in state_dict.items() if key.startswith(action_prefix)}
    categorized = len(direct) + len(nested) + len(action)
    uncategorized = sorted(set(state_dict) - {
        *(direct_prefix + key for key in direct),
        *(nested_prefix + key for key in nested),
        *(action_prefix + key for key in action),
    })

    alias_missing = sorted(set(direct) ^ set(nested))
    alias_shape_mismatches = []
    alias_storage_mismatches = []
    for key in sorted(set(direct) & set(nested)):
        if tuple(direct[key].shape) != tuple(nested[key].shape):
            alias_shape_mismatches.append(key)
        same_storage = (
            direct[key].untyped_storage().data_ptr() == nested[key].untyped_storage().data_ptr()
            and direct[key].storage_offset() == nested[key].storage_offset()
        )
        if not same_storage:
            alias_storage_mismatches.append(key)

    model_start = time.perf_counter()
    model = TICVLA(model_path=args.model, action_horizon_steps=30, train_vlm=False)
    model_construct_seconds = time.perf_counter() - model_start
    vlm_report = compare(direct, model.vlm.state_dict())
    action_report = compare(action, model.action_expert.state_dict())

    all_clean = not any(
        [
            uncategorized,
            alias_missing,
            alias_shape_mismatches,
            alias_storage_mismatches,
            vlm_report["missing_keys"],
            vlm_report["unexpected_keys"],
            vlm_report["shape_mismatches"],
            action_report["missing_keys"],
            action_report["unexpected_keys"],
            action_report["shape_mismatches"],
        ]
    )
    if not all_clean:
        report = {
            "all_clean": False,
            "checkpoint_load_seconds": checkpoint_load_seconds,
            "model_construct_seconds": model_construct_seconds,
            "checkpoint_total_keys": len(state_dict),
            "categorized_keys": categorized,
            "uncategorized_keys": uncategorized,
            "direct_vlm_alias": {
                "direct_key_count": len(direct),
                "nested_key_count": len(nested),
                "missing_or_extra": alias_missing,
                "shape_mismatches": alias_shape_mismatches,
                "storage_mismatches": alias_storage_mismatches,
            },
            "vlm": vlm_report,
            "action_expert": action_report,
        }
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        raise RuntimeError("checkpoint compatibility report is not clean")

    model.vlm.load_state_dict(direct, strict=True)
    model.action_expert.load_state_dict(action, strict=True)
    report = {
        "all_clean": True,
        "strict_load": True,
        "checkpoint_load_seconds": checkpoint_load_seconds,
        "model_construct_seconds": model_construct_seconds,
        "checkpoint_total_keys": len(state_dict),
        "categorized_keys": categorized,
        "uncategorized_keys": uncategorized,
        "direct_vlm_alias": {
            "direct_key_count": len(direct),
            "nested_key_count": len(nested),
            "missing_or_extra": alias_missing,
            "shape_mismatches": alias_shape_mismatches,
            "storage_mismatches": alias_storage_mismatches,
        },
        "vlm": vlm_report,
        "action_expert": action_report,
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
