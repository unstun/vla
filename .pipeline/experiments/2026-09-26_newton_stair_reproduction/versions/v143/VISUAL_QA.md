# Actual-zero video visual review

Reviewed the three original representative PNGs from the completed gpu5070ti replay.

- Frame0: native00.00s and video00.00s, startup initial_state; complete actual robot visible with the close camera. The physical witness records clock0.0 and step counter0, with identical before/after body/joint state hashes.
- Frame836: robot climbing the original stairs; cyan admitted local SCAN curve and orange global route visible; latest completed solve2.14ms.
- Frame1671: native55.92s, terminal arrived from Nav2, no active local curve after stopping; robot remains upright.

The full55.733s/1672-frame MP4 passed decode and all causal source indices. Startup retains actual preceding recorded states, then navigation preserves original wall timestamps. Actual physical v142 rerun arrived without a fall and verified applied-state copyback. Native navigation staysv139; this recording is separate from the six-run acceptance denominator.

Local regular MP4 bytes match the remote master SHA-256: `514f757cfe8c5994fccffda8930042799bfecd5d977dfa570790bb6cc2b34857`. Previousv140/v141 videos remain intact.
