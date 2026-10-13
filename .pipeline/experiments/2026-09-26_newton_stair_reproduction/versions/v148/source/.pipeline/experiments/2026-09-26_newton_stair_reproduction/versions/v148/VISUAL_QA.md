# Original-start full-route video visual review

Reviewed original representative frames0,1769,3538and an additional decoded72.0s frame.

- Frame0: original lower-floor spawn, native0.0s, actual factory initial state and close camera. It differs spatially from the earlier corner-only capture.
- Frame1769: actual stair traversal at native59.20s; original global turn visible, actual short admitted local plan is partly occluded by the robot. No substitute curve or altered coordinates.
- Additional72.0s video frame: cyan local curve clearly visible in front of the robot, orange global route visible; latest completed solve2.06ms. Original MP4 extraction SHA bound locally.
- Frame3538: native118.17s, original final upper-floor goal reached, arrived action and no active local curve after stop. Robot is upright and actual final measured PD hold passed.

The full117.9667s/3539-frame video passed decoding, all3539causal physical source indices, startup simulation/navigation wall clock separation, and nonfuture local curve events.2939frames have controller-admitted curve output. Pauses and both protected replacements remain visible. Actual physical path is76.883m from sensor-period body samples; the finer per-video-state body path is77.945m. These sampling definitions are distinct. No mid-route reset or stitched episode.

Firstv144original-start attempt remains FAILEDafter23.126m and itsv145video is retained. One freshv147episode passes original full-route arrival/no-fall/hold/copyback and both replacement proofs. This is not repeated full-route reliability or sustained30Hz acceptance. Regular local MP4 SHA256 matches the remote master:f7dbe6a319c24cf9d3caa6ddc98118b8eae547363c5124691709ebb7c6a002cb.
