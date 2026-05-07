from __future__ import annotations

import hashlib
import hmac
import os


def pseudonymize(value: str,prefix: str = "PX_",size: int = 16) -> str:
    """

    Pseudo-anonymises a value using HMAC-SHA256.

    Properties:
    -Deterministic: same input value => same pseudonym.
    -Not reversible without the secret.

    The secret is taken from DICOMSHIELD_SECRET.
    """
    secret = os.environ.get("DICOMSHIELD_SECRET")
    if not secret:
        raise RuntimeError(
            "DICOMSHIELD_SECRET is missing. Export the environment variable before running."
        )

    digest = hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{prefix}{digest[:size]}"

def remap_uid(uid: str) -> str:
    """
    Generates a DICOM UID derived from HMAC-SHA256.

    Uses DICOMSHIELD_SECRET so the mapping cannot be verified without the key.
    Root prefix 2.25.<decimal_integer> follows common practice for hash-derived UIDs.
    """
    secret = os.environ.get("DICOMSHIELD_SECRET")
    if not secret:
        raise RuntimeError(
            "DICOMSHIELD_SECRET is missing. Export the environment variable before running."
        )
    digest = hmac.new(
        secret.encode("utf-8"),
        uid.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    as_int = int(digest[:32], 16)
    return f"2.25.{as_int}"
