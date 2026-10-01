> ⚠ [未门控] Codex CLI 0.153.3 在当前沙箱初始化 app-server 时返回 Operation not permitted，未产生独立核查结论。主会话已核对摘要、实测字段、视频 SHA 和未实施方案边界；reviewed: false 保留。

## 2026-10-01: SCAN-Planner frequency source check

[SCAN-Planner, arXiv 2606.19555v1](https://arxiv.org/html/2606.19555v1)
was inspected for Dr Sun's local-rate question. The paper describes real-time
Jetson Orin NX operation but does not report fixed local replanning Hz or a
measured 30 Hz trajectory-update result. At author-code pin
`348e8a590a50a5a6bbab8d8c6dcfd171f009be26` (Apache-2.0), FSM/safety/controller
timers are 100/20/100 Hz; nominal trajectory generation is displacement/state/
safety triggered. Timer settings are not achieved trajectory rates. Status of
this source check: `surveyed`, not a new upstream reproduction. See the
[frequency survey](../survey/2026-10-01_scan_planner_frequency.md) for primary
paper/code links and the inspected previous-trajectory initialization branch.
The [Newton timing archive](../experiments/2026-10-01_newton_nav2_timing_archive.md)
separately records our failed full-stack 30 Hz/1:1 targets and delivered video.
