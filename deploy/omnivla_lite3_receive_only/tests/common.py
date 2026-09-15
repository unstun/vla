"""Test fixtures for the receive-only deployment."""


def minimal_jpeg(width: int = 3, height: int = 2) -> bytes:
    """Return a minimal JPEG marker stream accepted by the boundary parser."""

    sof_payload = bytes(
        [
            8,
            (height >> 8) & 0xFF,
            height & 0xFF,
            (width >> 8) & 0xFF,
            width & 0xFF,
            3,
            1,
            0x11,
            0,
            2,
            0x11,
            0,
            3,
            0x11,
            0,
        ]
    )
    length = len(sof_payload) + 2
    return b"\xff\xd8\xff\xc0" + length.to_bytes(2, "big") + sof_payload + b"\xff\xd9"


def trajectory():
    return [[float(index), float(-index), 1.0, 0.0] for index in range(8)]

