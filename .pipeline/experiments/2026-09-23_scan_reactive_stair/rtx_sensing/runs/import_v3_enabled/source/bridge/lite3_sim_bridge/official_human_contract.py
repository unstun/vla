"""Shared identity and hashing contract for the official Isaac human cache."""

import hashlib
import json


ISAAC_ASSET_ROOT = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/"
    "Isaac/5.1/Isaac"
)
CHARACTER_URL = (
    f"{ISAAC_ASSET_ROOT}/People/Characters/male_adult_police_04/"
    "male_adult_police_04.usd"
)
BIPED_URL = f"{ISAAC_ASSET_ROOT}/People/Characters/Biped_Setup.usd"
CACHE_SCHEMA_VERSION = 1


def cache_content_sha256(arrays) -> str:
    """Hash named arrays independently of the container file's ZIP metadata."""

    hasher = hashlib.sha256()
    for name in sorted(arrays):
        array = arrays[name]
        hasher.update(name.encode("utf-8"))
        hasher.update(str(array.dtype).encode("ascii"))
        hasher.update(json.dumps(list(array.shape)).encode("ascii"))
        hasher.update(array.tobytes(order="C"))
    return hasher.hexdigest()
