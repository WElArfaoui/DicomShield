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
    Generates a DICOM UID derived from hash.
        
    We use root 2.25.<decimal_integer>, common practice for UUID/hash derived UIDs.
    """
    # 128 bits of effective hash to keep reasonable size and stability.
    as_int = int(hashlib.sha256(uid.encode("utf-8")).hexdigest()[:32], 16)
    return f"2.25.{as_int}"