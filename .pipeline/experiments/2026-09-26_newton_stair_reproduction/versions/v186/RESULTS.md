# v186 result: rejected after five attempts

Stage: experiment and analysis. Five original-start routes on gpu5070ti;
only attempts03/05 arrived. Keep all source, logs and failed captures.
The declared terminal-crawl criterion passed4/5, but attempt04 still crawled
for5.477s inside5cm after curve expiry (median command about0.024m/s).
Small measured movement can prolong correction; the progress watcher is not a
hard duration bound.

24,717 actual model-input frames and full command histories match exactly,
with no gaps. Actual capture logs show one tolerance capture in attempt01 and
two captures in attempt04, including one no-measured-progress capture at
2.164cm error. Attempts02/03/05 had no capture events. Thus not every navigation
failure can be attributed to an activated terminal branch. The contemporaneous
unchanged v17706–10 control arrived5/5; this candidate is not adopted.

Component and actual graph tests passed (39 unique controller cases,42 colcon
entries, terminal regression,2 profiles,18 host checks). These are not a
substitute for physical route results. RL, stance, safety gates and route inputs
were unchanged. Native source remains frozen and all raw captures remain under
`gpu5070ti:/data/sun/vla_mppi_20261009/trials/v186_full_candidate_attemptNN/`.
Locally returned per-run `remote_artifacts.json` binds all293 files/symlinks.

Follow-up v187 removes local completion latching and restores v177 semantics.
Only prolonged tiny correction after expiry fails into the existing Nav2
measured-stop/replan protocol. It requires its own complete-route validation.
