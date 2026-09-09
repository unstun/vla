# Execution plan

1. Activate this task; verify pinned local source/assets and current server.
2. Build isolated official environments and acquire the pinned BF16 checkpoint.
3. Start official model server and default MuJoCo demo; inspect camera renders.
4. Freeze the case and run three bounded repetitions through the official client.
5. Preserve model/control/stop traces and paired native camera recordings.
6. Decode/inspect videos, return source/checkpoint/evidence and verify hashes.
7. Write `OPUS_RETURN.md`, clean up owned processes, and leave task at review.

Exact commands, limits, fallback boundaries and acceptance checks are in the
execution package. Preserve failed attempts. Rollback stops only task-owned
process groups and retains the isolated work directory and all evidence.
