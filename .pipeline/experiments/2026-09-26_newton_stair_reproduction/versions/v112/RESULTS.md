# Intrinsic mapping diagnosis

The original268 actually published clouds from v110 are replayed with their
exact captured sensor/body poses and unchanged native parameters. This is a
synchronous intrinsic-work control; higher-rate body messages and the live
physics/ROS scheduling context are not replayed. Every frame retains a map hash.

Total measured callback CPU17.286s matches wall17.288s. The largest nonstartup
cloud costs165.319ms CPU without a rolling-map shift. Other frames combine
69.517ms sliding with64.145ms cloud work. The slow map work therefore exists
without concurrent physics; this is not explained solely by CPU competition.
Fourteen multiaxis/wrapping/full-grid sliding controls supply baseline hashes.
No production optimization or full-route acceptance is claimed.
