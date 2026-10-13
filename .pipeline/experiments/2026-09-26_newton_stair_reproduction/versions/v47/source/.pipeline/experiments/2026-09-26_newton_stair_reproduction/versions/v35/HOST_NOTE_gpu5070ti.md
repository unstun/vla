# v35 trial host note

The environment, quiet-host gate, signal/abort handling and post-run recovery
from the reviewed v34 host note apply unchanged to v35. See
`../v34/HOST_NOTE_gpu5070ti.md` and the original port's `PORT.md`.

Dr Sun directed compilation to gpu5070ti and then requested the v35 video on
2026-09-30. The existing simulator environment and controller snapshot are
execution dependencies; no new private bytes are transferred for this trial.
No other compute/container task should overlap the trial. The launcher uses
the existing CPU Newton profile and native amd64 navigation container; the
GPU hostname does not mean GPU physics. No actual robot is controlled.

Launch the derived `v35_trial_run.sh` detached after the source/P1 gates.
Host records go under `versions/v35/host/<run ID>_*`. Only a pre-physics
infrastructure failure permits the next numbered attempt. Never overwrite
an existing run directory. Observe quietly, and SIGTERM the runner PID if
Dr Sun requests a stop. Keep all returned logs, including failed attempts.
