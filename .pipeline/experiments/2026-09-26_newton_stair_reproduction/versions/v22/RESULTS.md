# v22 component results

The host loader tests and Linux ROS tests pass. The actual sidecar publishes
126659 records after two advancing nonzero clock messages, with packed SHA-256
`b68527dd9d2ea8a4647c64aaf59b884da16364e41b146943c03f2c6da68cfa56`.
The original navigation payload remains
`97d2dfbdb60c91e8473ab57f348923360f139da1130b4e9b7dd57e8655c15ca2`.
An altered source is rejected; the preceding three source-pairing tests also
pass. See `publisher_test.log`, `test_dense_input.py`, and
`test_dense_publisher_ros.py`.

The exact dense payload with unchanged scan55 classification fails to continue
at the captured v21 stop: `audits/2026-09-27_v21_frontier/dense_raw_surface.json`.
This is an actual native replay with all 189 original paired scans. No physical
run is needed to promote this known-failing intermediate version; none was run.
Its source remains frozen and is not labeled a navigation success.

The subsequent full floor/riser source selection is isolated as v23.
