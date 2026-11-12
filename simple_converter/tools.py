"""Locate external programs (FFmpeg, LibreOffice, Calibre, UnRAR).

Explorer launches us with *its* PATH, which may be stale after a winget
install, so we also look in the usual install folders and cache the result.
"""
import glob
import json
import os
import shutil
import sys
from pathlib import Path

from .util import APPDIR

CONFIG = APPDIR / "tools.json"
LOCAL = os.environ.get("LOCALAPPDATA", "")
PF = [os.environ.get("ProgramFiles", r"C:\Program Files"),
      os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]


def _first(cands):
    for c in cands:
        for hit in sorted(glob.glob(c), reverse=True):
            if os.path.isfile(hit):
                return hit
    return None


def _find(name, extra):
    return shutil.which(name) or _first(extra)


def _bundled(name):
    """FFmpeg shipped next to SimpleConverter.exe by the installer."""
    if getattr(sys, "frozen", False):
        p = Path(sys.executable).parent / "ffmpeg" / f"{name}.exe"
        if p.is_file():
            return str(p)
    return None


def discover() -> dict:
    found = {
        "ffmpeg": _bundled("ffmpeg") or _find("ffmpeg", [
            rf"{LOCAL}\Microsoft\WinGet\Links\ffmpeg.exe",
            rf"{LOCAL}\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe",
            r"C:\ffmpeg\bin\ffmpeg.exe",
        ]),
        "soffice": _find("soffice", [rf"{p}\LibreOffice\program\soffice.exe" for p in PF]),
        "calibre": _find("ebook-convert", [rf"{p}\Calibre2\ebook-convert.exe" for p in PF]),
        "unrar": _find("UnRAR", [rf"{p}\WinRAR\UnRAR.exe" for p in PF]),
    }
    if found["ffmpeg"]:
        probe = Path(found["ffmpeg"]).with_name("ffprobe.exe")
        found["ffprobe"] = str(probe) if probe.exists() else shutil.which("ffprobe")
    else:
        found["ffprobe"] = None
    return found


def save(found: dict):
    CONFIG.write_text(json.dumps(found, indent=2), encoding="utf-8")


_cache = None


def get(name: str) -> str | None:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CONFIG.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _cache = {}
        if any(v and not os.path.isfile(v) for v in _cache.values()) or not _cache:
            _cache = discover()
            save(_cache)
    path = _cache.get(name)
    if path and os.path.isfile(path):
        return path
    # maybe installed since the cache was written
    _cache = discover()
    save(_cache)
    return _cache.get(name)


def available() -> set[str]:
    found = discover()
    save(found)
    return {k for k, v in found.items() if v}


def need(name: str) -> str:
    from .util import ConvertError
    p = get(name)
    if not p:
        nice = {"ffmpeg": "FFmpeg", "ffprobe": "FFmpeg", "soffice": "LibreOffice",
                "calibre": "Calibre", "unrar": "WinRAR"}[name]
        raise ConvertError(f"{nice} is not installed (needed for this conversion).")
    return p
