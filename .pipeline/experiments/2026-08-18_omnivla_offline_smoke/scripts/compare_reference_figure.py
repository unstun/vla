#!/usr/bin/env python
"""Compare a local edge run's figure against the authors' shipped reference.

`inference/1_ex_omnivla_edge.jpg` in the pinned upstream tree is the authors'
own rendered output for the default configuration (language prompt
"blue trash bin"), so it is a genuine reference for a default-configuration run
— but a *visual* one. Upstream ships no trajectory arrays, and the figure is a
matplotlib rendering, so differences from font/renderer/version drift are
expected and this is not a numeric trajectory check.

Layout (from run_omnivla_edge.py::save_robot_behavior): a 2x2 gridspec where
column 0 holds the two camera images and column 1 (gs[:, 1]) holds the
trajectory plot. The trajectory panel is therefore the right half.

Usage: compare_reference_figure.py <run_dir> [--reference <jpg>]
"""
import os, sys
import numpy as np
from PIL import Image

TP = "/Users/sun/tongbu/study/phdproject/vla/third_party/2026-08-18_omnivla_5182600"
REF = f"{TP}/OmniVLA/inference/1_ex_omnivla_edge.jpg"

run = sys.argv[1]
ref_path = sys.argv[sys.argv.index("--reference") + 1] if "--reference" in sys.argv else REF
loc_path = os.path.join(run, "1_ex_omnivla_edge.jpg")

ref = np.asarray(Image.open(ref_path).convert("RGB"), dtype=np.int16)
loc = np.asarray(Image.open(loc_path).convert("RGB"), dtype=np.int16)
if ref.shape != loc.shape:
    print(f"shape mismatch: reference {ref.shape} vs local {loc.shape}")
    sys.exit(1)

diff = np.abs(ref - loc)
h, w, _ = diff.shape
panel = diff[:, w // 2:, :]          # gs[:, 1] -> trajectory plot, right half

def stats(d, name):
    d = d.astype(np.float64)
    frac = float((d.max(axis=2) > 16).mean())
    print(f"{name}:")
    print(f"  mean abs pixel difference : {d.mean():.4f} / 255")
    print(f"  max  abs pixel difference : {int(d.max())} / 255")
    print(f"  pixels differing by > 16  : {frac*100:.4f} %")
    return d.mean(), d.max(), frac

print(f"reference: {ref_path}")
print(f"local    : {loc_path}")
print(f"size     : {w}x{h}\n")
stats(diff, "whole image")
print()
stats(panel, "trajectory panel (right half)")

heat = diff.max(axis=2).astype(np.float64)
heat = (heat / max(heat.max(), 1) * 255).astype(np.uint8)
out = os.path.join(run, "reference_figure_diff.png")
Image.fromarray(heat).save(out)
print(f"\nheat-map written: {out}")
