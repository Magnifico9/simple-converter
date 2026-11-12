"""Collect multi-selected files into one job.

Explorer starts one process per selected file. Each process drops its path into
a queue folder; the first one to grab the lock becomes the leader, waits until
no new files arrive for a moment, then processes all of them together. The
others exit immediately.
"""
import os
import re
import time
import uuid
from pathlib import Path

from .util import APPDIR

QDIR = APPDIR / "queue"


def collect(key: str, files: list[str], settle=0.8, max_wait=20.0) -> list[str] | None:
    QDIR.mkdir(parents=True, exist_ok=True)
    key = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
    for f in files:
        item = QDIR / f"{key}.{os.getpid()}.{uuid.uuid4().hex}.item"
        tmp = item.with_suffix(".tmp")
        tmp.write_text(f, encoding="utf-8")
        os.replace(tmp, item)

    lock = QDIR / f"{key}.lock"
    try:
        if lock.exists() and time.time() - lock.stat().st_mtime > 120:
            lock.unlink()
    except OSError:
        pass
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        return None  # someone else is collecting

    start = last_change = time.time()
    last_count = -1
    while True:
        time.sleep(0.15)
        count = len(list(QDIR.glob(f"{key}.*.item")))
        now = time.time()
        if count != last_count:
            last_count, last_change = count, now
        elif now - last_change >= settle or now - start > max_wait:
            break
    try:
        lock.unlink()
    except OSError:
        pass

    out = []
    for item in QDIR.glob(f"{key}.*.item"):
        try:
            out.append(item.read_text(encoding="utf-8"))
            item.unlink()
        except OSError:
            pass
    seen, uniq = set(), []
    for f in out:
        if f.lower() not in seen:
            seen.add(f.lower())
            uniq.append(f)
    return uniq
