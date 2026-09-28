# v23 physical result

`v23_building_route01` completes 89.962189 s of continuous recorded physics and
reaches its declared simulation bound without arrival. Displacement is
[0.122773, -1.208143, 0.101420] m. The command connection has zero reconnects,
protocol errors or I/O errors. Minimum body-up Z is 0.961760. Recorded stillness,
source identity, paired sensor artifacts and Linux state copyback verify.

No backend navigation terminal or completed driver artifact was produced before
the simulation bound. The original common reviewer raises FileNotFoundError on
that absent driver artifact; its raw exception is retained. The diagnostic copy
`audits/2026-09-27_v23_frontier/review_incomplete.py` treats the absence as a
failed check and writes a failing review, without altering the original source
or fabricating the missing artifact. `repair_outcome.json` is in the run folder.

The previous component tests remain valid within their declared recorded-input
scope. This fresh motion differs and exposes another physical-run failure.
No short-stair or complete-floor acceptance is claimed. The actual 30s state,
189 paired scans, latest emergency hold spline and original route are frozen in
`audits/2026-09-27_v23_frontier/inputs` for diagnosis.
