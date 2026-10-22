# Change boundary

Native changes live only in the v291 scan_nav2_controller overlay: tracking_node.hpp owns a hysteretic terminal brake state; LocalMotion exposes it; Controller calls command once and records its terminal status. Existing goal and measured-PD acceptance stay intact.

Stance changes live in v291 stance_hold.py and its versioned Newton adapter. Reuse immutable v216 StanceHold validation and state transitions, add an opt-in output adapter during STAND_SETTLING. A loaded foot (>=10 N) with quiet leg joints can latch a torque-matched target at original RL Kp/Kd; a foot losing >1 N support is released. No airborne leg is captured. Partial ownership is reported explicitly and last_action follows actual applied targets. Formal four-foot hold gating is unchanged.

One task owns this overlay, focused tests, captured-input scripts/results, and the existing HTML progress. No global/local planner algorithm or radius/freshness change, no policy retraining, no old snapshot modification. Component acceptance checks behavior, not new motion trajectories.
