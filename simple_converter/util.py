import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

APPDIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SimpleConverter"
APPDIR.mkdir(parents=True, exist_ok=True)
LOG = APPDIR / "simple-converter.log"
ROOT = Path(__file__).resolve().parent.parent
ICON = ROOT / "assets" / "simple-converter.ico"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ConvertError(Exception):
    pass


def log(msg: str):
    try:
        if LOG.exists() and LOG.stat().st_size > 2_000_000:
            LOG.unlink()
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg.rstrip() + "\n")
    except OSError:
        pass


def stem_of(src: Path) -> str:
    name = src.name
    if name.lower().endswith(".tar.gz"):
        return name[:-7]
    return src.stem


def unique_path(p: Path) -> Path:
    if not p.exists():
        return p
    stem, ext = p.name, ""
    if p.name.lower().endswith(".tar.gz"):
        stem, ext = p.name[:-7], ".tar.gz"
    else:
        stem, ext = p.stem, p.suffix
    i = 1
    while True:
        cand = p.with_name(f"{stem} ({i}){ext}")
        if not cand.exists():
            return cand
        i += 1


def out_path(src: Path, outdir: Path | None, ext: str, suffix: str = "") -> Path:
    d = outdir or src.parent
    d.mkdir(parents=True, exist_ok=True)
    return unique_path(d / f"{stem_of(src)}{suffix}.{ext}")


def out_folder(src: Path, outdir: Path | None, suffix: str) -> Path:
    d = outdir or src.parent
    p = d / f"{stem_of(src)}{suffix}"
    if p.exists():
        i = 1
        while (d / f"{stem_of(src)}{suffix} ({i})").exists():
            i += 1
        p = d / f"{stem_of(src)}{suffix} ({i})"
    p.mkdir(parents=True)
    return p


def run(cmd: list, timeout: float | None = None, cwd=None) -> str:
    cmd = [str(c) for c in cmd]
    log("RUN " + " ".join(cmd))
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd,
                           creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise ConvertError(f"{Path(cmd[0]).name} timed out")
    out = (r.stdout or b"").decode("utf-8", "replace")
    err = (r.stderr or b"").decode("utf-8", "replace")
    if r.returncode != 0:
        tail = "\n".join((err or out).strip().splitlines()[-6:])
        raise ConvertError(f"{Path(cmd[0]).name} failed: {tail}")
    return out


def tempdir() -> Path:
    base = APPDIR / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="cvt_", dir=base))


def parse_pages(spec: str | None, n: int) -> list[int]:
    """'1-3, 5, 8-' -> 0-based page indexes. Empty -> all pages."""
    if not spec or not spec.strip():
        return list(range(n))
    pages = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a = int(a) if a else 1
            b = int(b) if b else n
            pages.extend(range(a - 1, min(b, n)))
        else:
            pages.append(int(part) - 1)
    pages = [p for p in pages if 0 <= p < n]
    if not pages:
        raise ConvertError(f"Page range '{spec}' selects no pages (document has {n}).")
    return pages


TIME_RE = re.compile(r"^\d+(:\d{1,2}){0,2}(\.\d+)?$")


def parse_time(s: str | None) -> str | None:
    if not s or not s.strip():
        return None
    s = s.strip()
    if not TIME_RE.match(s):
        raise ConvertError(f"Bad time '{s}'. Use seconds (90) or mm:ss / hh:mm:ss.")
    return s


def natural_key(p) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(p))]
