> ⚠ [未门控] Codex CLI 0.153.3 在当前沙箱初始化 app-server 时返回 Operation not permitted，未产生独立核查结论。主会话已核对摘要、实测字段、视频 SHA 和未实施方案边界；reviewed: false 保留。

- [`2026-10-01_newton_nav2_timing_archive.md`](2026-10-01_newton_nav2_timing_archive.md)
  — v36-v46 Nav2 timing/CPU-graph/cache integration and actual-wall video.
  v40 CPU graph exactly matches 200 original closed-loop rows; CUDA v38 fails
  its fixed-target joint gate and is not adopted. Native v44 recorded replays
  pass safety/geometry checks at 11.8/12.8 ms, but complete physical v45 runs
  at local 16.86 Hz, raw controller 29.96 Hz, global PCT 1.00 Hz and RTF 0.9400,
  ending `global_refresh_failed:pct_no_route`. v46 delivers an ordinary
  57-second wall-timeline video; display 30 FPS/1:1 playback proves neither
  local 30 Hz nor simulation 1:1. No Building arrival; v3 remains accepted.
  Optimization proposals are archived, not implemented; v47 absent.
