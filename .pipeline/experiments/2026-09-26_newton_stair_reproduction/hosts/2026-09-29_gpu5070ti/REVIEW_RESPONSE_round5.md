# Response to the port's independent review, round 5 (`port_review_round5.json`, passed)

Round 5 confirmed the round-4 changes to the runner. It checked them against the version reviewed in round 4,
rebuilt from the round-3 dry copy (sha256 `d0fb8fb46471…`), and found two non-blocking points. Both were checked.
Only documents changed: the runner is still the reviewed `2649f0e8afbd…`. No physics ran.

- **N31, a residual route to B7's failure.** Confirmed by reading.
  - **The route:** if `run_bounded` ends while the episode runs, the runner reaches its post-run step with the
    episode alive. That step removes the main container under the live worker. The runner finds the episode only
    as `run_bounded`'s child.
  - **The three causes:** two are operator actions, stopping `run_bounded` alone or signalling the runner's process
    group, and the host note forbids both. The third is `run_bounded` dying by itself.
  - **Not guarded, and documented** in the host note as a residual risk. `run_bounded` only waits on its child and
    writes its record, and nobody else uses the host during the run. Every change to the runner after a passing
    round needs its own tests and review, and this risk does not justify another cycle before the trial.
  - **What would show it:** the post-run record shows the container recovered and removed, while `process.json` is
    missing.
  - **The two narrower cases** cannot remove a live container:
    - a SIGTERM in the microseconds between the launch and the runner storing its pid;
    - a `run_bounded` that stays alive without a child for 10 s.
- **N32, wording.** All three points were applied:
  - the host note now says what a group signal, or stopping `run_bounded` alone, would do: the post-run step would
    remove the container under the live worker;
  - the unprotected window before the handler also covers opening the log, after which the run ID cannot be
    reused, so a retry takes the next ID under the rule;
  - PORT.md's new sentence is rewrapped at 120 columns.
