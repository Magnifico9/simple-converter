"""Office documents via LibreOffice (headless)."""
import shutil
from pathlib import Path

from .. import tools
from ..formats import family_of
from ..util import APPDIR, ConvertError, out_path, run, tempdir

FILTERS = {
    "writer": {"pdf": "pdf:writer_pdf_Export", "docx": "docx:MS Word 2007 XML",
               "doc": "doc:MS Word 97", "odt": "odt", "rtf": "rtf",
               "txt": "txt:Text (encoded):UTF8", "html": "html:XHTML Writer File:UTF8",
               "epub": "epub"},
    "calc": {"pdf": "pdf:calc_pdf_Export", "xlsx": "xlsx:Calc MS Excel 2007 XML",
             "xls": "xls:MS Excel 97", "ods": "ods", "html": "html:HTML (StarCalc)"},
    "impress": {"pdf": "pdf:impress_pdf_Export", "pptx": "pptx:Impress MS PowerPoint 2007 XML",
                "ppt": "ppt:MS PowerPoint 97", "odp": "odp"},
}
INFILTER = {"html": "HTML (StarWriter)", "txt": "Text (encoded):UTF8"}
PROFILE = (APPDIR / "lo_profile").as_uri()


def soffice(src: Path, family: str, to: str, outdir=None, infilter=None, name_src=None) -> list[Path]:
    exe = tools.need("soffice")
    flt = FILTERS[family].get(to)
    if not flt:
        raise ConvertError(f"Can't convert to {to.upper()}")
    tmp = tempdir()
    try:
        cmd = [exe, f"-env:UserInstallation={PROFILE}", "--headless", "--norestore",
               "--nologo", "--nodefault", "--nolockcheck"]
        if infilter:
            cmd.append(f"--infilter={infilter}")
        cmd += ["--convert-to", flt, "--outdir", tmp, src]
        run(cmd, timeout=600)
        produced = [p for p in tmp.iterdir() if p.is_file()]
        if not produced:
            raise ConvertError("LibreOffice produced no output (file may be corrupt or locked)")
        dst = out_path(name_src or src, outdir, to)
        shutil.move(str(produced[0]), dst)
        return [dst]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def convert(src: Path, to: str, outdir=None) -> list[Path]:
    fam = family_of(src)
    if fam in ("writer", "calc", "impress"):
        return soffice(src, fam, to, outdir)
    if fam in ("html", "txt"):
        return soffice(src, "writer", to, outdir, infilter=INFILTER[fam])
    raise ConvertError(f"No office route for {src.suffix} -> {to}")


def from_html_text(html: str, src: Path, to: str, outdir=None) -> list[Path]:
    tmp = tempdir()
    try:
        h = tmp / (src.stem + ".html")
        h.write_text(html, encoding="utf-8")
        return soffice(h, "writer", to, outdir, infilter=INFILTER["html"], name_src=src)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def slides_to_images(src: Path, outdir=None, opts=None) -> list[Path]:
    from . import pdf
    tmp = tempdir()
    try:
        p = soffice(src, "impress", "pdf", tmp)[0]
        res = pdf.to_images(p, "png", outdir or src.parent, opts, suffix=" (slides)")
        # rename "x (slides)" folder/file to match the original name
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
