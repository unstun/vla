# Original full-route repeats: verified incomplete cohorts

Stage: experiment + analysis. Frozen v147 on gpu5070ti, original lower-floor
spatial start and full route. **The repeatability gate has not passed.** The
delivered successful attempt01 is excluded from both new cohorts. No navigation
code or parameters were changed during these repeats.

## Before reboot: declared attempts02–07

| Attempt | Verified outcome | Measured path | Native end | Fall | Maximum planning round |
|---|---|---:|---:|---|---:|
| 02 | FAILED | 35.422 m | 88.123 s | No | 377.403 ms |
| 03 | FAILED | 40.206 m | 83.486 s | No | 311.178 ms |
| 04 | FAILED | 49.389 m | 102.855 s | No | 374.452 ms |
| 05 | Raw result records FINISHED; closeout interrupted | Not qualified | 125.703 s | Not independently qualified | Not qualified |
| 06–07 | Unstarted | — | — | — | — |

The three closed runs have execution exit0, successful state copyback and
completed retention; navigation and the original full-route gate failed.
The original runner's exit1 is expected for navigation failure. These are
**0 arrivals among 3 closed trials**, not 0/6. Original interrupted progress is
untouched, including its stale active attempt05 marker.

Attempt05 records physical arrival and measured hold, but has no state-copyback,
supervisor-closeout or retention-completion evidence. Its 1,431 raw files
(551,145,821 bytes) and active marker are preserved. It is not promoted to a
passed trial or replaced. The former access-loss checkpoint is preserved in
`REPORT.interrupted_checkpoint.md`.

## After reboot: declared attempts08–13

| Attempt | Verified outcome | Measured path | Native end | Fall | Maximum planning round |
|---|---|---:|---:|---|---:|
| 08 | FINISHED; original full-route gate passed | 76.743 m | 145.283 s | No | 373.279 ms |
| 09 | FAILED | 61.642 m | 107.213 s | No | 499.624 ms |
| 10–13 | Unstarted; resource admission stopped the batch | — | — | — | — |

The separate post-reboot cohort has **1 arrival among 2 closed trials**. All
outcomes remain in the cohort. The runner stopped before attempt10 when other
GPU compute tasks appeared; it did not stop on navigation failure. Across 412
one-second samples, RAM available never fell below 22.80 GiB, swap use was zero,
and one-minute load peaked at 2.54. These samples describe this later cohort
only. Other work appeared during it, so do not label it idle throughout.

At 09:51:53 UTC the host had three other GPU compute tasks, about 13.93 GiB RAM
available, and no Docker containers. Both declared admission conditions
(no other GPU compute task and at least 20 GiB RAM available) prevent starting
the remaining four. No unrelated process was stopped.

## Integrity and claim boundary

The observed-only audit preserves original progress and verifies frozen v147
source (3,357 pairs, 618 runtime inputs), every native receipt file, every closed
raw inventory/hash, all archive members, original spatial/clock-zero start,
continuous state, final target, copyback and replacement stop proofs. All five
runs’ 29 recorded replacement owners have qualifying proof. This does not make
the four failed navigation results successful.

| Cohort | Closed raw files | Remote bytes | Archive members verified | Returned files | Returned bytes |
|---|---:|---:|---:|---:|---:|
| Before reboot | 873 | 871,693,678 | 2,429 | 45 | 1,317,219 |
| After reboot | 582 | 827,337,792 | 2,314 | 29 | 929,696 |

Every returned byte matches its remote SHA-256 manifest; see
`pre_reboot/return_verification.json` and `post_reboot/return_verification.json`.
Original incomplete progress is carried into each `RESULT.json`. Unstarted
trials are not counted, and cohorts are not combined into a population
reliability estimate. Remote roots:

- `/data/sun/vla_mppi_20261009/results/full_route_repeats_20261012`
- `/data/sun/vla_mppi_20261009/results/full_route_repeats_post_reboot_20261012`

Executed audit source SHA-256:
`07cc1a244765028572b3bfabc59d77029c99b709cdd9026e332475aa5b92b299`.
It ran with `--observed-only` for both roots. It changes no original run,
runner, protocol, active marker or progress file. Large raw records remain remote.

Full-route failures need separate captured-input recovery diagnosis; the first
two have different recorded symptoms. Host OOM/GPU load is not established as
their cause. See `../2026-10-12_gpu5070ti_freeze/REPORT.md` for continuous
computation around the power-key interval and the unresolved SSH outage.

Resume only unstarted attempts10–13 once admission passes, retaining 08/09 and
recording the interruption. Keep pre-reboot 06/07 labelled unstarted unless a
separate continuation is recorded. Main task remains in_progress; broader
reference, MPPI steps 2–5, 30 Hz and Jetson gates stay unchanged.


## Navigation continuation requested, 2026-10-12

Dr Sun set the host-incident investigation aside and asked to resume navigation
work. A separate unchanged-v147 continuation was prepared for attempts10–13,
with parent request/progress/outcome hashes and dead-parent checks. Six guard
tests pass on gpu5070ti. The detached continuation made31admission checks across
its bounded600-second wait and admitted none; it exited without creating any
new trial. Parent hashes and all four absent run paths were verified afterward.
See `RESUME_HOLD_RECEIPT.json` and `RESUME_QUALITY.json`. The recorded final
resource inspection recovered about22.89GiB RAM available, but another GPU task
was still active. The continuation is no longer running or waiting.

Read-only analysis meanwhile checked all five closed captures and actual native
source meanings. Failures02/04end with no usable trajectory;03/09end with negative
safety. Successful08also has safety/stale-evidence stops and recovers. Counts of
A-star bounds errors alone cannot explain failure because they also occur in08.
See `FAILURE_TRIAGE.md`; six compact files207,813bytes returned and hash verified.
No source fix or same-input native reproduction is claimed.

Next work: recover a reserved/eligible execution interval for the remaining four
unchanged runs; reconstruct failed09from original inputs before choosing a new
versioned repair. Do not rerun the already-used continuation control root or
replace08/09. A later admission attempt needs a new control record retaining
this failed admission; no attempt10–13has been consumed.
