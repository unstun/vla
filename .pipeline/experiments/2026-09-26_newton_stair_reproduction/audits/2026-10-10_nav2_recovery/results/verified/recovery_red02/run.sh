set -eo pipefail
source /opt/ros/foxy/setup.bash
source /task/baseline/install/setup.bash
cmake -S /repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery -B /task/results/recovery_red02/build -DTEST_SOURCE=/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-10_nav2_recovery/../../versions/v128/src/scan_nav2_controller/test/test_controller.cpp -DNATIVE_WORKSPACE=/task/baseline
cmake --build /task/results/recovery_red02/build -j2
set +e
/task/results/recovery_red02/build/recovery_regression --gtest_filter='PluginTest.NegativeSafetyTriggersRecoveryOnNextTick:PluginTest.NegativeCandidateProofTriggersRecoveryInAdmissionTick' --gtest_output=xml:/task/results/recovery_red02/tests.xml
code=$?
test "$code" = 1
