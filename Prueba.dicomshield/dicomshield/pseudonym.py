from __future__ import annotations

import hashlib
import hmac
import os


def pseudonymize(value: str, prefix: str = "PX_", size: int = 16) -> str:
    """
    Pseudoanonimiza un valor mediante HMAC-SHA256.

    Propiedades:
    - Determinístico: mismo valor de entrada => mismo pseudónimo.
    - No reversible sin el secreto.

    El secreto se toma de DICOMSHIELD_SECRET.
    """
    secret = os.environ.get("DICOMSHIELD_SECRET")
    if not secret:
        raise RuntimeError(
            "Falta DICOMSHIELD_SECRET. Exporta la variable de entorno antes de ejecutar."
        )

    digest = hmac.new(
        secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{prefix}{digest[:size]}"


def remap_uid(uid: str) -> str:
    """
    Genera un UID DICOM derivado de hash.

    Usamos raíz 2.25.<entero_decimal>, práctica común para UIDs derivados de UUID/hash.
    """
    # 128 bits efectivos del hash para mantener tamaño razonable y estabilidad.
    as_int = int(hashlib.sha256(uid.encode("utf-8")).hexdigest()[:32], 16)
    return f"2.25.{as_int}"
