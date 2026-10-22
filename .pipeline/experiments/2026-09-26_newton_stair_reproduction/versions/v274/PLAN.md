# v274 GPMP endpoint physical-factor preparation

Frozen v273 exposes start-pose heading collisions in CU08/CU13 and an approach
collision in CE04. Actual installed WNOJ/WNOA graph construction omits obstacle
factors at both endpoint keys while retaining soft endpoint derivative priors.
The proposed small treatment adds the existing physical obstacle factor at
both endpoints, with unchanged noise/geometry/requested poses. Endpoint layer
slots are separate from the interior obstacle-factor index sequence and must
not be appended to that sequence. Both GPMP orders require regression checks.

Implementation candidate: reuse the existing GPObstacleFactor at both endpoints
in physical-support mode, with the same0.1noise and cost threshold. Leave the
interior layer-index sequence unchanged. Both source files were verified against
frozen v272 before this local edit. No build/test/freeze or repaired-case claim
yet. Saved point audits remain isolated in v276 and do not change this model.
