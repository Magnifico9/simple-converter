"""Route an (op, target) pair to the right engine."""
import traceback
from pathlib import Path

from .engines import data, images, media, office, other, pdf
from .formats import canon, family_of
from .util import ConvertError, log

SLOW_FAMILIES = {"video", "audio", "writer", "calc", "impress", "ebook", "archive", "md", "html", "txt"}
SLOW_OPS = {"vid_compress", "aud_normalize", "pres_images", "pdf_compress", "pdf_merge"}
BATCH_OPS = {"pdf_merge", "img_combine_pdf"}


def is_slow(op, to, files):
    if op in SLOW_OPS:
        return True
    fams = {family_of(f) for f in files}
    if op == "convert" and ("pdf" in fams and to in ("docx", "epub")):
        return True
    return bool(fams & SLOW_FAMILIES) or len(files) > 10


def convert_one(src: Path, to: str, outdir=None, opts=None) -> list[Path]:
    opts = opts or {}
    fam = family_of(src)
    to = canon(to) if to != "tar.gz" else to
    same = canon(src.suffix) == to

    if fam in ("image", "svg"):
        if to in ("mp4", "webm"):
            return media.to_video(src, to, outdir, opts)
        return images.convert(src, to, outdir, opts, " (edited)" if same else "")
    if fam == "video":
        if same:
            return media.same_format_media(src, opts, outdir)
        if to == "gif":
            return media.to_gif(src, outdir, opts)
        if to in media.AUDIO_FMTS:
            return media.to_audio(src, to, outdir, opts)
        return media.to_video(src, to, outdir, opts)
    if fam == "audio":
        if same:
            return media.same_format_media(src, opts, outdir)
        return media.to_audio(src, to, outdir, opts)
    if fam == "subtitle":
        return media.subtitle(src, to, outdir)
    if fam == "pdf":
        if to == "pdf":
            return pdf.edit(src, outdir, opts)
        if to == "docx":
            return pdf.to_docx(src, outdir, opts)
        if to == "txt":
            return pdf.to_txt(src, outdir, opts)
        if to in ("png", "jpg"):
            return pdf.to_images(src, to, outdir, opts)
        if to == "epub":
            return other.ebook(src, to, outdir)
    if fam == "calc" and to in ("csv", "json"):
        return data.convert(src, to, outdir)
    if fam in ("writer", "calc", "impress", "txt"):
        return office.convert(src, to, outdir)
    if fam in ("csv", "json"):
        if to in ("xlsx", "json", "csv"):
            return data.convert(src, to, outdir)
        # csv -> ods/pdf: go through a temporary xlsx
        from .util import tempdir
        import shutil
        tmp = tempdir()
        try:
            x = data.convert(src, "xlsx", tmp)[0]
            return office.soffice(x, "calc", to, outdir, name_src=src)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if fam == "md":
        return data.md_convert(src, to, outdir)
    if fam == "html":
        if to == "md":
            return data.html_to_md(src, outdir)
        return office.convert(src, to, outdir)
    if fam == "ebook":
        return other.ebook(src, to, outdir)
    if fam == "archive":
        return other.archive(src, to, outdir)
    raise ConvertError(f"Don't know how to convert {src.suffix} to {to}")


def run_tool(op: str, src: Path, outdir=None, opts=None) -> list[Path]:
    opts = opts or {}
    if op == "img_compress":
        return images.compress(src, outdir)
    if op == "img_resize":
        return images.tool(src, "resize", outdir)
    if op == "img_rotate":
        return images.tool(src, "rotate", outdir)
    if op == "img_strip":
        return images.tool(src, "strip", outdir)
    if op == "vid_compress":
        return media.compress_video(src, outdir)
    if op == "vid_mute":
        return media.mute(src, outdir)
    if op == "vid_frame":
        return media.frame(src, outdir, opts)
    if op == "aud_compress":
        return media.compress_audio(src, outdir)
    if op == "aud_normalize":
        return media.normalize(src, outdir)
    if op == "pdf_split":
        return pdf.split(src, outdir, opts)
    if op == "pdf_compress":
        return pdf.compress(src, outdir, opts)
    if op == "pdf_images":
        return pdf.extract_images(src, outdir)
    if op == "pres_images":
        return office.slides_to_images(src, outdir, opts)
    raise ConvertError(f"Unknown action {op}")


def run(op: str, to: str, files: list[Path], opts: dict | None = None, progress=None):
    """Returns (outputs, errors) where errors is a list of (file, message)."""
    opts = opts or {}
    outdir = Path(opts["outdir"]) if opts.get("outdir") else None
    outputs, errors = [], []

    if op in BATCH_OPS:
        try:
            fn = pdf.merge if op == "pdf_merge" else images.combine_pdf
            outputs += fn(files, outdir)
        except Exception as e:
            errors.append((None, _msg(e)))
        return outputs, errors

    for i, f in enumerate(files):
        if progress:
            progress(i, len(files), f)
        try:
            if op == "convert":
                outputs += convert_one(f, to, outdir, opts)
            else:
                outputs += run_tool(op, f, outdir, opts)
        except Exception as e:
            errors.append((f, _msg(e)))
    return outputs, errors


def _msg(e: Exception) -> str:
    if isinstance(e, ConvertError):
        log(f"ERROR {e}")
        return str(e)
    log("CRASH " + traceback.format_exc())
    return f"{type(e).__name__}: {e}"
