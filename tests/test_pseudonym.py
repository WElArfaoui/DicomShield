"""HMAC-based pseudonymisation must be deterministic and key-dependent."""

from __future__ import annotations

import os

import pytest

from dicomshield.pseudonym import pseudonymize


def test_deterministic_same_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DICOMSHIELD_SECRET", "test-secret-please-rotate")
    a = pseudonymize("PATIENT-001")
    b = pseudonymize("PATIENT-001")
    assert a == b
    assert a.startswith("PX_")
    assert len(a) == len("PX_") + 16


def test_different_inputs_diverge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DICOMSHIELD_SECRET", "test-secret-please-rotate")
    assert pseudonymize("A") != pseudonymize("B")


def test_secret_changes_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DICOMSHIELD_SECRET", "secret-1")
    out1 = pseudonymize("PATIENT-001")
    monkeypatch.setenv("DICOMSHIELD_SECRET", "secret-2")
    out2 = pseudonymize("PATIENT-001")
    assert out1 != out2


def test_missing_secret_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DICOMSHIELD_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="DICOMSHIELD_SECRET"):
        pseudonymize("PATIENT-001")


def test_custom_prefix_and_size(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DICOMSHIELD_SECRET", "test-secret")
    out = pseudonymize("PATIENT-001", prefix="ANON_", size=8)
    assert out.startswith("ANON_")
    assert len(out) == len("ANON_") + 8
