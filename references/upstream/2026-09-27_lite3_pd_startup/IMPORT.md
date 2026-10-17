# Lite3 SDK startup source import

- Repository: https://github.com/DeepRoboticsLab/Lite3_MotionSDK
- Branch/commit: main / `b30a3ec09619e1dd0f3cfa6c49a50eb59670f141`.
- License: MIT, unchanged `LICENSE` included.
- All selected files are exact raw commit bytes; hashes and URLs are in
  `source_identity.json`. No dirty sibling checkout was copied.
- Original prerequisites/commands: see the retained `README.md` and
  `CMakeLists.txt`. The full hardware example uses C++11, Eigen, the Linux
  architecture-specific DeepRobotics shared SDK, pthread, math and realtime
  libraries; its documented CMake build and `Lite_motion` executable are not
  a macOS simulation command. No hardware sender or receiver was executed.

Local reuse lives in the Newton policy experiment's `build_sdk_spline.py` and
`pd_startup.py`. The builder extracts the final `MotionExample::CubicSpline`
method byte for byte and compiles it with a small C ABI using Apple clang.
The generated method, wrapper, binary, compiler and build command are hashed.
This avoids linking the SDK's platform-specific network or hardware code.

The local phase adapter follows `PreStandUp`/`StandUp` durations, preparation
pose, desired-velocity finite difference and PD gains. Explicit adaptations are
the initial one-second passive damping phase, standing to the already pinned
policy Q0, measured readiness and a 0.25-second PD torque handoff. These are
simulation integration choices, not claims of an unchanged full SDK deployment.
The original source files remain unmodified.

Rebuild with the existing Newton Python environment and
`.pipeline/experiments/2026-09-26_newton_macos_policy/scripts/build_sdk_spline.py`.
Run `test_pd_startup.py` through the experiment's bounded runner. The scalar
reference is independently compared against SciPy CubicHermiteSpline.

Evidence labels: `imported` for this source snapshot; scalar build/testing and
bounded Newton integration are recorded separately under
`.pipeline/experiments/2026-09-26_newton_stair_reproduction/repairs/2026-09-27_pd_startup/`.
