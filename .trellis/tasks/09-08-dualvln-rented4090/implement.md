# Execution

1. Import pinned upstream, create isolated work/environment, verify source synchronization.
2. Download original checkpoint and required encoder weight, verify sizes and SHA-256.
3. Run original realworld-agent fixture inference in BF16 and retain raw actions/trajectories plus GPU/timing evidence.
4. Select and record a small simulator scene, validate camera/action mapping, run the bounded closed loop and encode video.
5. Return and hash-check local artifacts, inspect video frames, report actual outcome and any incomplete gate. Preserve existing work.
