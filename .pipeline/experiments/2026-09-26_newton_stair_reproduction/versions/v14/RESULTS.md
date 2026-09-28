# v14 results

The actual v13 admission order reproduced the reply-consumer bug. Three of four
focused tests failed before the change; all four pass after it. All four native
fault receiver tests and seven existing runtime stop-flow tests also pass.
Evidence is under `evidence/`.

Native SCAN is unchanged from v13. Physical end-to-end confirmation is pending
the next inherited integration run; this version does not claim stair success.
