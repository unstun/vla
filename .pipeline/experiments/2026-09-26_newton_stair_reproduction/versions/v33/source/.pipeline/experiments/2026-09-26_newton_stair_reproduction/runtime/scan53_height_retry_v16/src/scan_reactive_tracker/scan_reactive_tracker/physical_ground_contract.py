"""Identity of the complete finite ground payload for the pinned Building map."""
import hashlib

PHYSICAL_GROUND_TOPIC = "/tracker_ground"
PHYSICAL_GROUND_POINTS = 149_504
MAX_GROUND_POINTS = 200_000
PHYSICAL_GROUND_SHA256 = "b357cd1317f06f73758e31d05613a55e204e4e5e05c17dcd5a4fcca140676313"


def verify_physical_ground(data: bytes, frame: str, width: int, height: int,
                           point_step: int, row_step: int, is_bigendian: bool,
                           fields: dict) -> None:
    expected_fields = {name: (offset, 7, 1) for name, offset in
                       (("x", 0), ("y", 4), ("z", 8), ("intensity", 12))}
    if frame != "world" or width != PHYSICAL_GROUND_POINTS or height != 1 or \
       point_step != 16 or row_step != 16 * width or is_bigendian or fields != expected_fields or \
       len(data) != 16 * PHYSICAL_GROUND_POINTS or \
       hashlib.sha256(data).hexdigest() != PHYSICAL_GROUND_SHA256:
        raise ValueError("physical ground payload/schema/frame differs from the pinned Building contract")
