"""Ebooks (Calibre) and archives."""
import shutil
import tarfile
import zipfile
from pathlib import Path

from .. import tools
from ..formats import ext_of
from ..util import ConvertError, out_path, run, stem_of, tempdir


# --- ebooks ------------------------------------------------------------------
def ebook(src: Path, to: str, outdir=None) -> list[Path]:
    exe = tools.need("calibre")
    dst = out_path(src, outdir, to)
    try:
        run([exe, src, dst], timeout=1800)
    except ConvertError:
        if dst.exists():
            dst.unlink()
        raise
    return [dst]


# --- archives ----------------------------------------------------------------
def _extract(src: Path, dest: Path):
    e = ext_of(src)
    try:
        if e == "zip":
            with zipfile.ZipFile(src) as z:
                z.extractall(dest)
        elif e == "7z":
            import py7zr
            with py7zr.SevenZipFile(src, "r") as z:
                z.extractall(dest)
        elif e in ("tar", "tar.gz", "tgz"):
            with tarfile.open(src) as t:
                t.extractall(dest, filter="data")
        elif e == "rar":
            run([tools.need("unrar"), "x", "-y", "-idq", src, str(dest) + "\\"], timeout=3600)
        else:
            raise ConvertError(f"Unsupported archive {e}")
    except ConvertError:
        raise
    except Exception as ex:
        raise ConvertError(f"Can't open archive: {ex}")


def _pack(folder: Path, dst: Path, to: str):
    files = [p for p in folder.rglob("*")]
    if to == "zip":
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in files:
                z.write(p, p.relative_to(folder))
    elif to == "7z":
        import py7zr
        with py7zr.SevenZipFile(dst, "w") as z:
            for p in folder.iterdir():
                z.writeall(p, p.name) if p.is_dir() else z.write(p, p.name)
    elif to == "tar.gz":
        with tarfile.open(dst, "w:gz") as t:
            for p in folder.iterdir():
                t.add(p, p.name)
    else:
        raise ConvertError(f"Can't create {to}")


def archive(src: Path, to: str, outdir=None) -> list[Path]:
    tmp = tempdir()
    try:
        _extract(src, tmp)
        dst = out_path(src, outdir, to)
        try:
            _pack(tmp, dst, to)
        except Exception as e:
            if dst.exists():
                dst.unlink()
            raise ConvertError(f"Can't create {to}: {e}")
        return [dst]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
