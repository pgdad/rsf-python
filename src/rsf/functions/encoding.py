"""Encoding intrinsic functions: States.Base64Encode, States.Base64Decode, States.Hash."""

from __future__ import annotations

import base64
import hashlib

from rsf.functions.registry import intrinsic


_SUPPORTED_ALGORITHMS = {"SHA-1", "SHA-256", "SHA-384", "SHA-512", "MD5"}
_ALGORITHM_MAP = {
    "SHA-1": "sha1",
    "SHA-256": "sha256",
    "SHA-384": "sha384",
    "SHA-512": "sha512",
    "MD5": "md5",
}


@intrinsic("States.Base64Encode")
def states_base64_encode(data: str) -> str:
    """Base64 encode a string."""
    if not isinstance(data, str):
        raise TypeError("States.Base64Encode: argument must be a string")
    return base64.b64encode(data.encode("utf-8")).decode("ascii")


@intrinsic("States.Base64Decode")
def states_base64_decode(data: str) -> str:
    """Base64 decode a string."""
    if not isinstance(data, str):
        raise TypeError("States.Base64Decode: argument must be a string")
    return base64.b64decode(data).decode("utf-8")


@intrinsic("States.Hash")
def states_hash(data: str, algorithm: str) -> str:
    """Hash data with the specified algorithm.

    Supported algorithms: SHA-1, SHA-256, SHA-384, SHA-512, MD5.
    """
    if not isinstance(data, str):
        raise TypeError("States.Hash: first argument must be a string")
    if algorithm not in _SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"States.Hash: unsupported algorithm '{algorithm}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_ALGORITHMS))}"
        )
    h = hashlib.new(_ALGORITHM_MAP[algorithm])
    h.update(data.encode("utf-8"))
    return h.hexdigest()
