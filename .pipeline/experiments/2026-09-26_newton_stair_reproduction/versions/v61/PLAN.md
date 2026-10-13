# v61 display-only framing correction

Physical source stays frozen v59, renderer source stays frozen v51. Preserve v60's close-camera render: it removes ceiling occlusion but crops the rear legs. Keep the lower0.60m camera height; use trail1.10m, ahead0.25m, down0.20m, original0.5s yaw smoothing and60degree FOV. Replay the same v59 states/times without physics, source-image manipulation or runtime changes. Verify first/middle/last whole-robot visibility, exact frame/time/state identity, and full MP4 decode. Keep failed videos remote with provenance; return only the usable review.
