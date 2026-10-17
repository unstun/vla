# v199 results

ControllerServer is the single Twist publisher. The plugin now computes and returns commands, and only clears execution on cancellation/failure.

Four selected ROS packages built. 65 distinct regression cases passed (72 colcon report entries including wrappers), including four real ControllerServer publication tests, existing goal/progress tests, launch wiring and 300 tracking parity samples. See `verification/` for raw logs and XML results.

The first build attempt exposed C++17 and explicit-message-construction requirements in the new test; both were corrected before freezing. No production algorithm change was required.

No physics or full-route experiment. GoalChecker PD hold integration remains the next version.
