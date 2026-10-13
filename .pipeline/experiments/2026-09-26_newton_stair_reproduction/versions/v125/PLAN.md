# Linux ROS logging and writer visibility

Parent: frozen v124. v124 completed the real factory stand at 11.020823 s,
then stopped before navigation after pct_support exited. Concurrent Foxy ROS
logging initialization races when its log directory is absent: a direct remote
12-process reproduction failed 3 initializations; a pre-created directory failed
0/12. Pre-create a run-owned ROS_LOG_DIR and ROS_HOME before starting nodes.

Run native ROS as the host UID/GID, with an equally owned private applied-state
tmpfs, so host evidence and writer inspection have a single user owner. Preserve
all safety gates and exact native binaries. For retained artifacts, the scoped
lsof wrapper exempts only mounted Docker network namespaces and internal overlay roots
from stat. The requested run-file paths on /data/sun remain fully inspected. All other errors remain fatal.
Test actual concurrent ROS initialization, host/native output writes and active
writer detection before freezing. Preserve original failed attempts and raw data.
