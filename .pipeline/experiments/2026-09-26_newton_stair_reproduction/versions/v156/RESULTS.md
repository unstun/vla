# Stationary start isolated by the world-aligned search lattice

The actual native replay reproduces the rejected first path and all6prefix
proposals. Current body yaw-2.72894166773rad is clear. Nominal proposed yaw
-2.09545741rad rejects. Direct cylinder evidence identifies support_gap_mask
as the veto (the ordinary support association passes). The terrain-inflation
hypothesis was not supported; no mask or obstacle-classification change follows.

All8ordinary start edges reject. All8additional knight-move edges also reject;
the two admissible start headings have blocked whole segments. A65-direction
probe (64uniform plus exact measured yaw) finds8clear5cm segments,5clear10cm,
5clear20cm and0clear30cm under the original path-heading rule. Keeping the body
yaw fixed permits38/32/33/31directions respectively, but that hypothetical
sideways controller is not implemented or proposed in v157. Instead test one
body-aligned lattice retry after ordinary search proves its start isolated.

776published scans through88.582946777s; fixed query88.812820440s, measured body
88.802825928s. Map digest60d90323f40674968b32554eb7b43ce004667b31162c09c538851c8faa25cd7a.
Exact asynchronous snapshot/clock scheduling is not restored. Failed source
trial is fully archived and verified (291files;557cd3ebf072d926aa5b929180e0725aef3db9d1bb9310cea2ee9c9ec8c64fb5).
