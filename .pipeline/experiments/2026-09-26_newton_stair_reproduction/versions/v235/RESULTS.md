# v235 gpu40901 single original-route attempt

Status: **FAILED before navigation goal**. Offline readiness passed; physical
full-route acceptance did not. Exactly one physics attempt was executed.

## Identity and preflight

Frozen v232 navigation, v216 locomotion and v233 physical/driver behavior;
v234 rebuilt native image/install, factory adapter and isolated Python.
RL SHA7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b,
original historical_full start/goal,0.35m collision/support guards, original
sensor period, controller/goal gates and600s recording limit unchanged.

Actual native graph/profile preflight passed12s with zero physics. Source/input
and installed-file hashes passed. A first entry attempt waited for preflight
port release; it ran no physics. The unique physical launch ledger prevents
another full-route invocation.

## Physical result

Run: v235_linux_full_attempt01. Last retained video state:12.801543235778809s;
227 states and16 completed scans. Recorder process exits1 after68.575703476s
wall time, including construction/compilation/startup. Original exception:
`Captured scan did not finish before the next sensor period`.

The goal was never sent. result.json and finish_request.json were not written;
shared-state terminal verification therefore fails. The45–55s stair window,
route arrival and terminal PD were not exercised. No automatic rerun occurred.
The failed pending-scan latency is not recorded. Completed scans span39.6–83.1ms;
CPU affinity/load is a diagnosis lead, not an established exclusive cause.

## Retention and delivery

Heavy source/capture/install remain on40901 under
/home/ubuntu/sun/vla_v234_20261017. Global lsof inaccessible-mount warnings
prevented inherited pruning. A separate verified7,615,632-byte non-pruning
snapshot preserves every original file; no source result was synthesized.
See [physical audit](../../audits/2026-10-17_v235_gpu40901_physical/RESULTS.md).
The accepted physical baseline remains v232/v233 on5070Ti.
