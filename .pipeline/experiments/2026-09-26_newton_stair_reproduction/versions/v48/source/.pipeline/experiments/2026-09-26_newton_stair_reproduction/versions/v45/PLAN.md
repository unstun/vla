# v45: actual navigation recording from initialized physical state

Version parent v44; entrypoint source parent v42. Adopt v44 complete-callback cache after actual contract and geometry checks. Increase the native process group CPU quota from 4 to 6 on the 8-core/16-thread 9700X, preserving physics and sensing computation and all timing/freshness gates. Keep original 1 ms physics, 20 ms policy, 30 Hz local/controller and 1 Hz global settings. Fix the raw-command timing observer to the actual P2BStampedTwist ROS type.

The delivered navigation video begins after original factory initialization. Keep original factory timing in startup_pacing.json; anchor the navigation pacing ledger to the actual initialized native state and wall time without resetting native time or physical state. Measure the complete navigation/sensing/transport loop from that anchor. No startup-speed claim, no hidden discarded physical steps, no pose interpolation.

Recording is bounded to native time 90 seconds, including about 11 seconds of factory initialization; delivered video shows only navigation samples. Retain v42 failed timing evidence. Full arrival remains unvalidated by a bounded video.
