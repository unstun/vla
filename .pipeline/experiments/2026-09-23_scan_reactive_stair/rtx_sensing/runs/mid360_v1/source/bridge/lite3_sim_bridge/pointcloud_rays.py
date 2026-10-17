"""ROS ray-cloud bytes derived only from paired measured first-return clouds."""
import struct
from collections import Counter


def ray_cloud_data(raw_be, obstacles_be):
    if len(raw_be) % 12 or len(obstacles_be) % 12:
        raise ValueError('XYZ payload must contain complete float32 triples')
    raw = list(struct.iter_unpack('!3f', raw_be))
    obstacles = Counter(struct.iter_unpack('!3f', obstacles_be))
    if obstacles - Counter(raw):
        raise ValueError('obstacle cloud is not a subset of the paired raw cloud')
    flags = [int(point in obstacles) for point in raw]
    if sum(flags) != sum(obstacles.values()):
        raise ValueError('ambiguous duplicate-point classification')
    return b''.join(struct.pack('<3fB3x', *point, flag) for point, flag in zip(raw, flags))
