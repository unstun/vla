# PRD: Handheld takeover and VLA-stop arbitration

## Goal

Allow the Retroid handheld to remain available during VLA operation and always
override or stop the autonomous command path with fail-closed behavior.

## Requirements

- Inventory both local APK variants and the actual handheld before selection;
  record hash, package/version/signature evidence, ABI, and rollback copy.
- Verify APK installation and UDP packet reception before motor use.
- Define a single command arbiter with explicit priorities: latched stop,
  handheld manual command, guarded VLA command, zero/default safe state.
- A stop disables VLA command consumption, expires the last command, and
  transitions the lower controller to the reviewed safe state.
- Apply command TTL, heartbeat watchdogs, source identity, sequence checks, and
  explicit manual re-arm.
- Test normal and fault cases without autonomous motion before any suspended or
  ground motion test.

## Acceptance criteria

- [ ] Compatible APK is installed and its packets are captured and decoded.
- [ ] Arbitration truth table covers simultaneous inputs and communication or
      process failures.
- [ ] Automated tests prove VLA cannot override a latched stop or manual mode.
- [ ] A human test demonstrates stop/takeover through the final runtime path
      before VLA-driven motion is eligible for approval.

## Out of scope

- Claiming that killing only the VLA server is an emergency stop.
- Relying on Wi-Fi as the sole physical safety mechanism.
