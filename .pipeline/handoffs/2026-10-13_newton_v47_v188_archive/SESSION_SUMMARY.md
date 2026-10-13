# Archive brief: Newton navigation v47–v188

Archive date: 2026-10-13 07:05 America/Los_Angeles. Work covered: 2026-10-01 (after commit
`943d0a9bb`, 01:34 PDT; v47–v51 results are dated 10-01) to 2026-10-13.
Stage: experiment + analysis. The records show no training, no Jetson connection and no
real-robot actuation (`latest_nav2_robot_actuated: false`; RL model unchanged).

- Local source of truth: `/Users/sun/tongbu/study/phdproject/vla` (version index
  `.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/{README.md,current.json}`).
- gpu5070ti execution copies only: `/home/sun/vla_exec/vla` (code/runtime copy) and
  `/data/sun/vla_mppi_20261009` (heavy raw trials, native builds, video masters).
- Mac ARM64 also ran physics for local reproductions (for example v114, v160, v164, v174, v176,
  v179–v183). Name the host when citing a result.

## User decisions in this archive session

1. Dr Sun asked what had been done, then: "commit and archive v47–v188 first".
2. Scope is only v47–v188: files changed after commit `943d0a9bb` (2026-10-01 01:34 PDT).
   The pre-Oct-1 untracked backlog (about 52k files, about 9 GB) stays uncommitted.
3. Heavy raw bytes stay local behind path-specific ignore entries plus a SHA-256 manifest,
   `.pipeline/handoffs/2026-10-13_newton_v47_v188_archive/LOCAL_ONLY_BYTES.json` (written by the
   main session; it is authoritative for which paths are local-only). Compact files and review
   MP4s are committed.
4. Housekeeping found: a stale 0-byte `.git/index.lock` (2026-10-01 02:46, no git process) had
   blocked staging since 10-01; about 2.06 GiB of `tmp_pack` garbage remains in `.git`.
   `current.json`/`README.md` still called v187 "running"; the main session corrected that and
   added the v188 entry.

## Version chain by phase (numbers from each version's RESULTS.md and the index)

### v47–v85: 30 Hz local-planning push (failed); v48 stays the reference
- v47 feasible-window reuse (gpu5070ti): local 16.232 Hz, controller 30.001 Hz, global 0.99987 Hz,
  RTF 0.94494; first seed-search failures 73.69% -> 0.22%; 22.73 m, no arrival.
- v48 remaining-curve warm start: median 3.092 ms, P95 126.496 ms, P99 207.175 ms, local
  15.859 Hz. Still `current: v48` in current.json.
- v49 rejected (cooperative budget broke the stop contract); v50 live maxima 1829.626/858.031 ms;
  v51 artifact storage pipeline (display/storage only); v52 10.19 Hz successful plans.
- v57 old corner passed twice (46.20/46.62 m), 25.65/25.76 Hz. v58/v59 best successful planning
  27.53/26.43 Hz with maxima 659.526/1236.709 ms; v59 has a 1.099 s late pause. v60/v61 display only.
- v62–v83 Mac work: v64–v66 fail before physics, v67/v68 stop on heartbeat_stale; v70 trace
  23.423 Hz, max 1316.856 ms; v71–v77 pinned upstream planning-core probe and corner-start
  fixture (upstream arm stalls after 1.13 m); v78 map profiling; v79–v83 mapping snapshots,
  v82 fails continuity (11.114/10.959 Hz).
- v84/v85 mapping admission: latest-only admission rejected (loses occupied cells under stalls);
  v85 three-thread prototype is component-only.
- Not reached: sustained 30 Hz, tail elimination, full-route arrival.

### v86–v121: actual Foxy Nav2 integration
- v86–v99 Foxy plugins, PCT GlobalPlanner, mission gateway, BT nodes, ARM64 builds; physics fails
  on several integration faults, each fixed in its own version.
- v100–v113 original-scene repairs (clock lane, body admission, proof/spline pairing, mapper rate);
  v110 14.347 m path; v113 22.835 m, FAILED before goal.
- v114 (Mac, original Building corner start): first Nav2 arrival, 26.551 m path, measured stop,
  two protected retries. v115–v121 are video/HTML deliveries (no new physics).

### v122–v164: MPPI-style steps parked; recovery repair; first original-start arrivals
- v122 typed diagnostics; v123–v125 gpu5070ti port. MPPI step 2 (v126) and step 3 (v127) parked;
  six-run repeats: v122 0/6 (one fall), v127 1/6.
- Recovery repair v128–v139. Support-gap fix: v134 static support veto (pilots 0/3), v135
  couples the global PCT route to it (pilots 2/3). v139 is validated for its declared fixed
  corner scenario: pilots 3/3, fresh candidate 6/6 vs baseline 5/6, 0 falls; maximum candidate
  round 706.406 ms.
- v144 original spatial start FAILED at 23.126 m. v147 (prefix proposals 3 -> 6, gpu5070ti): first
  original-start full-route arrival, 76.883 m, 118.207 native s; v148 video. Unchanged v147
  repeats did not qualify (0/3 before host reboot, 1/2 after).
- v149–v164 local recovery: v160 trial02 is the first Mac original full-route finish (77.571 m
  sensor path; 1/2 local trials); v162 Linux 1/5; v164 Mac arrival.
- Arrival chain: v147 first original-start arrival (Linux) -> v160 Mac 1/2 -> v174 Mac PASS with
  qualified stop proofs -> v177 Linux 5/5.

### v165–v178: repeated original-route qualification
- v165 Linux 0/5. v166–v173 ports, short reverse intent, transport and frame fixes.
- v174 (Mac): local full-route gate PASS (not the first Mac finish), 77.343536 m sensor path,
  140.287674 s, four stop proofs and four budget renewals.
- v175 Linux 2/5, not adopted. v176 (Mac) local spline finish radius 15 cm -> 2 cm: one PASS,
  77.659 m.
- v177 (Linux, v176 profile over v175 binaries): 5/5 original-route arrivals, 30 measured-stop
  handoffs, 0 falls; paths 76.846/76.946/77.097/76.871/76.910 m. Longest low-speed pause
  10.694 s; planning rounds up to 497.846 ms. Recovery candidate.
- v178 display-only full video of v177 attempt01: 162.367 s, 4,871 frames, 19,986,833 bytes.

### v179–v188: stop-cause, policy-only and terminal-capture audits
- v177 stop-cause audit: 35 revocations (30 retries, 5 final stops); 20 expired map source,
  3 fresh-input geometry, 3 progress timeouts, 4 first-curve timeouts. Run01 moved 0.956651 m
  under effective zero command, so 5/5 does not validate stopped-pose holding.
- v179 policy-only Mac trials at 0.2/0.35/0.5 m/s (low-speed controls); late >5 cm flags flat
  4/12, stairs 7/12. v182 at 0.6/0.8/1.0 m/s: flat 0/12 (max 3.67 cm), stairs 4/12 (max
  10.08 cm). v180/v181/v183 are display only. RL-input audit: 30,741 frames; zero-command maximum
  excursion 0.958 m.
- Terminal capture: v184 (Mac, 3 cm capture + latch) was refused before physics on missing
  frozen metadata. On gpu5070ti from the original start: v185 3/5, crawl 2.219 s, rejected;
  v186 2/5, crawl 5.477 s, rejected; v187 3/5, endpoint criterion 5/5 (max 1.579132 s), timeout
  branch exercised once and that run still arrived; v187 is not accepted (reviewed candidate only).
- Controls: unchanged v177 binary (attempts 06–10) 5/5, max crawl 0.7996 s. v188 unchanged-source
  rebuild (all 649 native sources equal v177) 3/5, endpoint 4/5, max crawl 4.997253 s.
  Failures occur without new endpoint logic; the cause of the variation is unknown.

## Claim boundaries
- `validated`: v3 one 12 m empty-floor run; v139 declared fixed corner scenario; v177 declared
  original-map/original-start repetition (5/5, one cohort).
- Not validated: sustained 30 Hz and tail elimination, general recovery, other maps, zero-command
  drift/standing hold, Jetson receive-only, real robot, any VLA integration.
- Cohorts are never pooled; Mac and Linux counts stay separate; failed attempts are retained.

## Open questions
1. Why the unchanged-source v188 rebuild fails 2/5 while the v177 binary cohort passed 5/5.
2. Repeated "safety stop, then no admitted trajectory" failures in v185–v188.
3. Zero-command drift (about 0.96 m) and RL standing behaviour on stairs.
4. Whether to promote v177 over the v48 reference; 30 Hz and long solve tails remain open.
5. Jetson access is still pending from Dr Sun.

## Pointers
- Reviews: `audits/2026-10-13_terminal_repair_review/REPORT.zh.md`,
  `audits/2026-10-12_v177_stop_causes/REPORT.zh.md`, `audits/2026-10-13_v177_rl_speed/REPORT.zh.md`.
- Surveys: `.pipeline/survey/2026-10-08_*` to `2026-10-13_terminal_capture_upstream_survey.md`.
- Previous archive: `.pipeline/handoffs/2026-10-01_newton_v36_v46_archive/SESSION_SUMMARY.md`.

Archive quality gate: Codex CLI 0.153.3 (`codex exec -s read-only --ephemeral`, default model) returned PASS
after the gate summary was extended with source-verified facts. [模型回退] claude-opus-5-5 is not a
Codex model, so `-m` was omitted; `--full-auto` no longer exists in this CLI.
