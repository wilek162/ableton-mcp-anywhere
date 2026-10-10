"""Locate the Ableton Live *User Library*, including relocated ones.

The stock `ableton-live-mcp install` only looks in
`Documents/Ableton/User Library` (Windows) or `Music/Ableton/User Library`
(macOS). A relocated library breaks it. Live records the real location, so we
read it back out of Live's own `Library.cfg` and a few well-known folders.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_PROJECT_PATH_RE = re.compile(r'<ProjectPath\s+Value="([^"]+)"\s*/>', re.IGNORECASE)


@dataclass(frozen=True)
class Candidate:
    """A possible User Library, and where the guess came from."""

    path: Path
    origin: str

    def __str__(self) -> str:  # pragma: no cover - display helper
        return f"{self.path} ({self.origin})"


def _roaming_ableton_dirs() -> list[Path]:
    """Directories where Live keeps its Preferences/Library.cfg, newest first."""
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Ableton"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Preferences" / "Ableton"
    else:
        root = Path.home() / ".ableton"
    if not root.is_dir():
        return []
    versions = sorted(
        (p for p in root.iterdir() if p.is_dir() and re.match(r"Live\s", p.name, re.I)),
        key=lambda p: _version_key(p.name),
        reverse=True,
    )
    return [v / "Preferences" for v in versions]


def _version_key(name: str) -> tuple:
    parts = re.findall(r"\d+", name)
    return tuple(int(p) for p in parts)


def _project_paths_from_cfg() -> list[Path]:
    """Every ProjectPath Live has recorded across its Library.cfg files."""
    found: list[Path] = []
    for prefs in _roaming_ableton_dirs():
        cfg = prefs / "Library.cfg"
        if not cfg.is_file():
            continue
        try:
            text = cfg.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for raw in _PROJECT_PATH_RE.findall(text):
            path = Path(raw.replace("\\", os.sep).replace("/", os.sep))
            if path not in found:
                found.append(path)
    return found


def _default_dirs() -> list[Path]:
    docs = "Documents" if sys.platform == "win32" else "Music"
    return [Path.home() / docs / "Ableton" / "User Library"]


def _search_roots() -> list[Path]:
    roots = list(_project_paths_from_cfg())
    # A relocated library usually lives on the same drive as the projects.
    for path in _project_paths_from_cfg():
        if path.is_absolute() and path.drive:
            roots.append(Path(path.anchor))
    if sys.platform == "win32":
        roots += [Path("C:\\"), Path("D:\\"), Path("E:\\")]
    seen, ordered = set(), []
    for r in roots:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered


def _looks_like_user_library(path: Path) -> bool:
    return path.is_dir() and path.name.lower() == "user library"


def candidates() -> list[Candidate]:
    """All plausible User Library locations, most likely first."""
    results: list[Candidate] = []

    def add(path: Path, origin: str) -> None:
        if any(path == c.path for c in results):
            return
        results.append(Candidate(path=path, origin=origin))

    for d in _default_dirs():
        add(d, "default location")

    # Walk each recorded project folder looking for a sibling "User Library".
    for base in _project_paths_from_cfg():
        for parent in [base, *base.parents][:6]:
            if parent == Path(parent.anchor):
                continue
            add(parent / "User Library", f"from Live project path {base}")

    # Last resort: a shallow drive scan for a ".../Ableton/User Library" folder.
    for root in _search_roots():
        try:
            for child in root.glob("*"):
                if not child.is_dir():
                    continue
                guess = child / "User Library" if child.name.lower() == "ableton" else None
                if guess and _looks_like_user_library(guess):
                    add(guess, f"scanned under {root}")
                if child.name.lower() == "user library" and _looks_like_user_library(child):
                    add(child, f"scanned under {root}")
        except OSError:
            continue

    return results


def remote_scripts_dir(user_library: Path | None = None) -> Path:
    """Resolve the `Remote Scripts` directory for the given/detected User Library."""
    override = user_library or os.environ.get("ABLETON_USER_LIBRARY")
    if override:
        base = Path(override).expanduser()
        if base.name.lower() == "remote scripts":
            return base
        return base / "Remote Scripts"
    for cand in candidates():
        if cand.path.is_dir():
            return cand.path / "Remote Scripts"
    raise FileNotFoundError(
        "Could not find your Ableton Live User Library. "
        "Open Live > Settings > Library to see its location, then pass it with "
        "--user-library or set ABLETON_USER_LIBRARY."
    )


def find_user_library(user_library: Path | None = None) -> Candidate:
    """Return the resolved User Library, or the first candidate with its origin."""
    override = user_library or os.environ.get("ABLETON_USER_LIBRARY")
    if override:
        base = Path(override).expanduser()
        if base.name.lower() == "remote scripts":
            base = base.parent
        return Candidate(path=base, origin="--user-library / ABLETON_USER_LIBRARY")
    for cand in candidates():
        if cand.path.is_dir():
            return cand
    first = candidates()[0]
    raise FileNotFoundError(
        f"Could not find your Ableton Live User Library (tried {first}). "
        "Pass --user-library or set ABLETON_USER_LIBRARY."
    )
