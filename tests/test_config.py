"""Profile loading reads YAML and exposes the documented attributes."""

from __future__ import annotations

from pathlib import Path

from dicomshield.config import load_profile


def _write_profile(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "profile.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def test_load_minimal_profile(tmp_path: Path) -> None:
    profile = load_profile(_write_profile(tmp_path, "policies: {}\n"))
    assert profile.tag_actions == {}
    assert profile.remove_private_tags is True
    assert profile.recurse_sequences is True
    assert profile.remap_uids is True
    assert profile.reject_burned_in_yes is False


def test_load_full_profile(tmp_path: Path) -> None:
    profile = load_profile(_write_profile(tmp_path, """
policies:
  remove_private_tags: false
  recurse_sequences: false
  reject_burned_in_yes: true
uids:
  remap: false
tag_actions:
  "(0010,0010)":
    action: replace
    value: ANONYMOUS
"""))
    assert profile.remove_private_tags is False
    assert profile.recurse_sequences is False
    assert profile.reject_burned_in_yes is True
    assert profile.remap_uids is False
    assert profile.tag_actions == {
        "(0010,0010)": {"action": "replace", "value": "ANONYMOUS"}
    }


def test_load_invalid_tag_format_raises(tmp_path: Path) -> None:
    import pytest
    with pytest.raises(ValueError, match="Invalid tag format"):
        load_profile(_write_profile(tmp_path, """
tag_actions:
  PatientName:
    action: replace
    value: ANONYMOUS
"""))
