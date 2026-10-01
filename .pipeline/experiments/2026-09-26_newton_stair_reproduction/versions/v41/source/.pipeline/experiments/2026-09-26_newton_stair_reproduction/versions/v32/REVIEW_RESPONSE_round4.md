# Response to independent review round 4 (`independent_review_round4.json`, passed)

Round 4 passed with no blocking finding and three non-blocking ones. All three were fixed before the freeze.
Two of the fixes change the pre-registered L1 judge, so the changed files go back to the reviewer for a
confirmation round, following round 1's N12 (edits after a review are reviewed again). v32's code, K1–K3 and
the diagnosis record are unchanged.

- **N1, the hold rule's limits.** PLAN.md now states them under class 2 and in the claim boundary:
  - **Subtracting all waiting:** *w* subtracts every thread's CPU waiting. A hold that overlaps at least
    *W* − 110 ms of such waiting is classed as scheduling.
  - **Short holds:** holds up to about 100 ms beyond the watchdog's 10 ms sleep are not class 2, and
    collections of that length are left to criterion 1.
  - **What the bound includes:** *W* − *w* − 10 ms also includes timer lateness and the watchdog's own work.
- **N2, an incomplete watchdog log.** `l1/evaluate_l1.py` now checks the wake-up log's coverage.
  - An interval without a wake-up on both sides is labelled `watchdog_log_incomplete` (class 0), not
    classified.
  - If the log does not span the loop, from the first step's start to the last step's end, the outcome is
    `inconclusive`.
  - Its `watchdog_coverage` block reports the wake-up count, the span and the number of incomplete
    intervals.
- **N3, tying the check to the judge.** `l1/synthetic_check.py` records the SHA-256 of the `evaluate_l1.py` it
  ran, and a fifth run was added:
  - **"watchdog_cut":** the benign run plus a scheduling-type step at step 5,000, with the log cut at step
    3,000. The step after the cut is labelled `watchdog_log_incomplete`, and the outcome is inconclusive.
  - **All five runs** match their expected classes and outcomes (`synthetic_check.json`, all_passed true,
    `evaluate_l1_sha256` ef4a4b3a…, equal to the file's current hash).
