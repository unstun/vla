# v31 first candidate (scan63), superseded

This directory keeps the first v31 candidate, `runtime/scan63_input_refresh_v31`,
and its version records as they were when the first independent review failed
them on 2026-09-28. Nothing here was frozen, and no physical episode ran on
it.

## What is here

- `PLAN.md`, `materialize.py`, `freeze.py` and `trial_signatures.py`: the
  first versions.
- `changes.patch`, `parent_source/`, `prepared.json` and `build_stdout.log`:
  the first materialization and build.
- `COMPONENT_RESULTS.md`: steps 1–4 as recorded then.
- `input_refresh_contract/`: the first contract.
  - Its probe source, requests and outputs (`red_v30/`, `green_v31/`).
  - `summary_first_judgement.json` and `analyze_first_judgement.py`: the
    first judgement.
  - `analyze.py` and `summary.json`: the corrected judgement.

  These scripts ran from `versions/v31/input_refresh_contract/`. Their
  relative paths (the pending inputs and the stop-class audit) refer to that
  location.

## Related runs

These ran on scan63 and stay under `runs/` with their own records:
- `runs/v31_saved_states01`;
- `runs/v31_native_regression01`, and `runs/v31_native_regression02`, the
  same suite rerun with no other container at its start and end
  (`alone_check.txt` sampled only those two moments);
- `runs/v31_native_regression02_attempt01_domain233`, the first start of
  `02`, rejected by Fast DDS at start-up;
- `runs/v31_regression_timing_control01`, the paired A* wall-time control
  (v30 and scan63 probes alternating).

## Why it was superseded

The first independent review (`../independent_review_round1.json`) found four
blocking problems:
- **B1:** `materialize.py` rewrote the three files that mix CRLF and LF lines
  in text mode and removed all 2,651 CR bytes. So `changes.patch` and
  `parent_source/` did not reproduce v30's bytes. The conversion is
  semantically inert, but the record was inexact.
- **B2:** the green C4 expectation was untested.
- **B3:** `freeze.py` did not pin the diagnosis rows or the timing control.
- **B4:** the design deviated from option 1 as offered, and no record showed
  Dr Sun accepting it.

It also raised nine non-blocking findings (N1–N9). Among them: the drain order
could pair a scan with the previous pose, take errors were fatal, and the
contract never exercised the inner sites.

Dr Sun kept the narrower design and asked for every finding to be fixed. The
code fixes changed the build, so v31 was re-materialized byte-exactly as
scan64 and every check was rerun (`../PLAN.md`, `../COMPONENT_RESULTS.md`).
