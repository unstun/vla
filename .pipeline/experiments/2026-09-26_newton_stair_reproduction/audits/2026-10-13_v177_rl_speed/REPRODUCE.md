# Reproduce this recorded-data audit

Local code is the source of truth; gpu5070ti stores the five original captures
and the compact extraction under the paths in `provenance.json`. No simulator
or policy inference needs to run. Do not overwrite original captures.

1. Run `extract.py --task /data/sun/vla_mppi_20261009 --output FRESH_OUTPUT` on
   gpu5070ti with Python 3. Each raw member is streamed and hash-checked; actual
   observation/ONNX command values and all ten history frames are checked.
2. Run `analyze.py --data FRESH_OUTPUT --output FRESH_ANALYSIS` with the existing
   Mac Newton Python recorded in provenance (NumPy and SciPy). The bounded local
   projection is approximately 17 MiB; full captures stay remote. The original
   35-event ledger is read from the neighboring 2026-10-12 audit.
3. Run `test_analysis.py` or unittest discovery in the audit directory. Three
   tests cover command categories, cubic-curve interpretation and corrupt input.
4. Run `make_report.py --analysis FRESH_ANALYSIS` from a working audit copy with
   an existing Python containing Matplotlib and NumPy. Set `MPLCONFIGDIR` and
   `XDG_CACHE_HOME` to owned temporary directories. On this host the source's
   STHeiti font gives Chinese plot labels; no runtime environment was modified.
   This produces all 35 event plots, CSVs and `speeds.html`.
5. Review actual curves and selected-event behavior. For a browser preview,
   serve only this report directory on `127.0.0.1`, not the whole research tree.

The newest command occupies input[87:90], not the first or last three elements
of the 450-element input: history is grouped by observation term. Source links
and hashes are in provenance. Durations use post-step time intervals without
merging across gaps. The first captured interval assumes one 20 ms policy step;
it precedes the first navigation command and does not affect stop conclusions.

Exact raw command vectors are matched in the preceding 0.3 s; identical repeated
values can have multiple candidate messages. Do not call this unique message-ID
causality. Curve phase subtracts observed yaw pauses from trajectory age and is
diagnostic. The prolonged endpoint cases also fit the actual position-error
correction, with roughly one policy-step pose alignment uncertainty.

Keep true zero, in-place yaw, finite boundary transitions, endpoint corrections
and unqualified longer boundary intervals distinct. Do not pool overlapping
stop-event windows into independent trials, or treat configured 0.6 m/s as a
measured universal RL stability threshold.
