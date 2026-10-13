# v167: native recovery tests pass; local full route interrupted

The recorded v165/01 stop admits a5cm backward curve (0.607381s,306samples),
publishes reverse intent, and passes full normal/fixed-heading collision, PVA,
dynamics and owner/input guards. Earlier stair/corner cases also pass. Actual
controller regression changes old vx0/yawrate1 into backward vx/zero yawrate.
14packages,47colconentries,18hosttests and actualgraph/mappedlibraries pass.

Mac full01 stops at48.145simseconds from an applied-state ACK timeout; no arrival
and no native recovery-branch physical coverage established. Receiver committed
sequence1857 after353ms, whereas host only acknowledged1856. Copyback is explicitly
unqualified; full result.json missing. All288raw files archived and SHA-verified
(142602240bytes,5a4a3a659ba63b31988331d248a3555ea44637a0d24b8571dd3a6a117c33e3c9).
v169 addresses Mac ACK wait separately; nativev167 remains frozen.
