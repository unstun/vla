# v79 compact state polling

Parent v76/native v63, backend behavior parent v59. Keep control, ownership,
watchdog and stop handlers unchanged. Produce summaries for default /state;
write each full PCT record once to pct_plan_history.jsonl. Explicit
/state?include_history=1 preserves the full retained 50-plan detail. Tests
cover HTTP routing, full/summary contents, failures, races and source ASTs.
Source is frozen after component checks; no physical acceptance is implied.
