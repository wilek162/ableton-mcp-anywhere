import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ableton_anywhere import library  # noqa: E402


def test_default_candidates_include_documents_library():
    cands = library.candidates()
    assert any(c.origin == "default location" for c in cands)
    # The very first default candidate is the standard Documents location.
    assert cands[0].path.name == "User Library"


def test_detects_relocated_library_from_library_cfg(tmp_path, monkeypatch):
    # A relocated library on E:, with the project folder Live records.
    relocated = tmp_path / "ABLETON" / "User Library"
    relocated.mkdir(parents=True)
    live_prefs = tmp_path / "Ableton" / "Live 12.4.6" / "Preferences"
    live_prefs.mkdir(parents=True)
    (live_prefs / "Library.cfg").write_text(
        f'<ContentLibrary><ProjectPath Value="{tmp_path / "ABLETON"}" />'
        "</ContentLibrary>",
        encoding="utf-8",
    )
    monkeypatch.setattr(library, "_roaming_ableton_dirs", lambda: [live_prefs])

    resolved = library.find_user_library()
    assert resolved.path == relocated
    assert "project path" in resolved.origin


def test_explicit_override_beats_everything(tmp_path, monkeypatch):
    explicit = tmp_path / "My Library"
    explicit.mkdir()
    monkeypatch.setenv("ABLETON_USER_LIBRARY", str(explicit))
    resolved = library.find_user_library()
    assert resolved.path == explicit


def test_remote_scripts_dir_from_override(tmp_path):
    lib = tmp_path / "User Library"
    scripts = library.remote_scripts_dir(lib)
    assert scripts == lib / "Remote Scripts"


def test_remote_scripts_dir_accepts_remote_scripts_path(tmp_path):
    scripts = tmp_path / "Remote Scripts"
    assert library.remote_scripts_dir(scripts) == scripts
