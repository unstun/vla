# v140 video review

Display source v139_candidate_attempt08: fifth fresh candidate trial, arrived,
three protected replacements. The recorded navigation timeline is54.867s,
1646frames/30FPS, no retiming or pose interpolation. Exact model isv40, matching
the recording. Display-only replay advances zero physics steps.

Actual EGL context and four controller/overlay selection tests pass. Full MP4
decode/count passes. Every1646causal source index and every displayed curve's
original event time are verified. Cyan curves are visible on1349frames; they
clear at revoked/expired-owner output and final hold. Parent/input hashes match
before and after replay. First, midpoint, final and initial turn previews have
been viewed: robot body/legs and stairs are visible; cyan local and orange global
paths are distinct; final frame reports arrived and clears the local curve.

The returned MP4 is an actual regular file,6,555,740bytes, and its SHA-256 matches
the retained master. Master and raw capture stay atgpu5070ti:/data/sun/vla_mppi_20261009.
This display version changes no navigation behavior or acceptance denominator.
