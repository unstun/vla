"""Derives the round-4 dry-test copies of v33_trial_run.sh (port review round 4, N27-N29).

Every difference from the runner is one of the exact replacements below, each asserted to occur the stated number
of times, so `diff v33_trial_run.sh checks/runner_dry4.sh` shows all of it:
- scratch outputs under ~/vla_exec/port/runner_dry4, and the run IDs runner_dry01 to 09;
- GRACE 5 s instead of 60 s, so the escalation test takes seconds;
- a recording podman first on PATH (checks/fd_recording_podman.sh, installed by the tests), which lists the
  descriptors each podman process inherits (N29);
- in place of the launcher, one call through the docker shim with the lock's descriptor closed, as Python's
  subprocess closes it for the episode's own calls, and then checks/standin_run_bounded2.py.
runner_dry4_oldlog.sh also opens the runner log without append mode, as before round 4: the control for N27.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

LAUNCH = '''VLA_SHIM_LOG="${P}_docker_calls.txt" "$PY" scripts/run_bounded.py --run-id "$RUN" --deadline 1800 -- \\
  "$PY" "$E/scripts/run_local_episode.py" \\
  --backend-executor single --applied-transport zmq --native-build "$E/runtime/scan64_input_refresh_v31" \\
  --geometry-obstacles --scene building_full --building-route historical_full --goal-wall-budget 1500 \\
  --startup-mode factory_pd --stance-hold --planner-config "$E/versions/v33/building_planner.yaml" \\
  --integration-version v33 < /dev/null &
'''
STANDIN = '''VLA_SHIM_LOG="${P}_docker_calls.txt" docker ps > /dev/null 9>&-
"$PY" "$E/hosts/2026-09-29_gpu5070ti/checks/standin_run_bounded2.py" "$V/runs/$RUN" < /dev/null &
'''
DRY = [
    ("# v33's single trial on gpu5070ti",
     "# DRY TEST COPY (round 4: stand-in launcher that prints run_bounded's record; scratch outputs) of v33's single"
     " trial on gpu5070ti", 1),
    ("V=$E/versions/v33/host\n", "V=$HOME/vla_exec/port/runner_dry4\n", 1),
    ("  v33_historical_full0[1-9]) ;;", "  runner_dry0[1-9]) ;;", 1),
    ("$E/runs/$RUN", "$V/runs/$RUN", 5),
    ("GRACE=60 ", "GRACE=5 ", 1),
    ("export PATH=$HOME/vla_exec/bin:$PATH\n",
     "export PATH=$HOME/vla_exec/bin:$PATH\nexport PATH=$HOME/vla_exec/port/runner_dry4/bin:$PATH\n", 1),
    (LAUNCH, STANDIN, 1),
]
OLDLOG = [
    ("# DRY TEST COPY (round 4:", "# DRY TEST COPY (round 4 control for N27, the runner log opened without append mode:", 1),
    ('exec >> "${P}_runner.log" 2>&1\necho "runner pid $$"', 'exec > "${P}_runner.log" 2>&1\necho "runner pid $$"', 1),
]


def apply(text, replacements):
    for old, new, count in replacements:
        found = text.count(old)
        assert found == count, (old, found, count)
        text = text.replace(old, new)
    return text


dry = apply((HERE.parent / "v33_trial_run.sh").read_text(), DRY)
(HERE / "runner_dry4.sh").write_text(dry)
(HERE / "runner_dry4_oldlog.sh").write_text(apply(dry, OLDLOG))
print("wrote runner_dry4.sh and runner_dry4_oldlog.sh")
