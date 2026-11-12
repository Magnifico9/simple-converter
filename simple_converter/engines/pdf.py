from pathlib import Path

import pymupdf as fitz

from ..util import ConvertError, out_folder, out_path, parse_pages


def _open(src: Path):
    try:
        doc = fitz.open(src)
    except Exception as e:
        raise ConvertError(f"Can't open PDF: {e}")
    if doc.needs_pass:
        raise ConvertError("PDF is password protected")
    return doc


def to_docx(src: Path, outdir=None, opts=None) -> list[Path]:
    from pdf2docx import Converter
    opts = opts or {}
    doc = _open(src)
    pages = parse_pages(opts.get("pages"), doc.page_count) if opts.get("pages") else None
    doc.close()
    dst = out_path(src, outdir, "docx")
    cv = Converter(str(src))
    try:
        if pages:
            cv.convert(str(dst), pages=pages)
        else:
            cv.convert(str(dst))
    except Exception as e:
        raise ConvertError(f"PDF to Word failed: {e}")
    finally:
        cv.close()
    return [dst]


def to_txt(src: Path, outdir=None, opts=None) -> list[Path]:
    doc = _open(src)
    pages = parse_pages((opts or {}).get("pages"), doc.page_count)
    text = "\n\f\n".join(doc[i].get_text("text", sort=True) for i in pages)
    doc.close()
    if not text.strip():
        raise ConvertError("No text found (the PDF is probably scanned images)")
    dst = out_path(src, outdir, "txt")
    dst.write_text(text, encoding="utf-8")
    return [dst]


def to_images(src: Path, fmt: str, outdir=None, opts=None, suffix=" (pages)") -> list[Path]:
    opts = opts or {}
    dpi = int(opts.get("dpi") or 150)
    doc = _open(src)
    pages = parse_pages(opts.get("pages"), doc.page_count)
    outs = []
    if len(pages) == 1:
        targets = [out_path(src, outdir, fmt)]
    else:
        folder = out_folder(src, outdir, suffix)
        width = max(3, len(str(doc.page_count)))
        targets = [folder / f"{src.stem}-{i + 1:0{width}d}.{fmt}" for i in pages]
    for i, dst in zip(pages, targets):
        pix = doc[i].get_pixmap(dpi=dpi, alpha=False)
        if fmt == "jpg":
            pix.save(dst, jpg_quality=int(opts.get("quality") or 90))
        else:
            pix.save(dst)
        outs.append(dst)
    doc.close()
    return outs if len(outs) == 1 else [targets[0].parent]


def merge(files: list[Path], outdir=None) -> list[Path]:
    if len(files) < 2:
        raise ConvertError("Select two or more PDFs to merge")
    out = fitz.open()
    for f in files:
        d = _open(f)
        out.insert_pdf(d)
        d.close()
    dst = out_path(files[0].parent / "Merged.pdf", outdir, "pdf")
    out.save(dst, garbage=3, deflate=True)
    out.close()
    return [dst]


def split(src: Path, outdir=None, opts=None) -> list[Path]:
    doc = _open(src)
    pages = parse_pages((opts or {}).get("pages"), doc.page_count)
    folder = out_folder(src, outdir, " (split)")
    width = max(3, len(str(doc.page_count)))
    for i in pages:
        one = fitz.open()
        one.insert_pdf(doc, from_page=i, to_page=i)
        one.save(folder / f"{src.stem}-{i + 1:0{width}d}.pdf", garbage=3, deflate=True)
        one.close()
    doc.close()
    return [folder]


def compress(src: Path, outdir=None, opts=None) -> list[Path]:
    opts = opts or {}
    doc = _open(src)
    dpi = int(opts.get("dpi") or 150)
    try:
        doc.rewrite_images(dpi_threshold=dpi + 10, dpi_target=dpi,
                           quality=int(opts.get("quality") or 70), lossy=True, lossless=True)
    except (AttributeError, TypeError):
        pass  # older PyMuPDF: just do structural compression
    dst = out_path(src, outdir, "pdf", " (compressed)")
    doc.save(dst, garbage=4, deflate=True, deflate_images=True, deflate_fonts=True,
             clean=True, use_objstms=1)
    doc.close()
    return [dst]


def edit(src: Path, outdir=None, opts=None) -> list[Path]:
    """Advanced: keep page range and/or rotate pages."""
    opts = opts or {}
    doc = _open(src)
    pages = parse_pages(opts.get("pages"), doc.page_count)
    doc.select(pages)
    rot = int(opts.get("rotate") or 0)
    if rot:
        for p in doc:
            p.set_rotation((p.rotation + rot) % 360)
    dst = out_path(src, outdir, "pdf", " (edited)")
    doc.save(dst, garbage=3, deflate=True)
    doc.close()
    if opts.get("compress"):
        res = compress(dst, outdir, opts)
        dst.unlink()
        res[0] = res[0].rename(dst)
        return [dst]
    return [dst]


def extract_images(src: Path, outdir=None) -> list[Path]:
    doc = _open(src)
    seen, folder, n = set(), None, 0
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen:
                continue
            seen.add(xref)
            try:
                data = doc.extract_image(xref)
            except Exception:
                continue
            if not data or data.get("width", 0) < 16 or data.get("height", 0) < 16:
                continue
            if folder is None:
                folder = out_folder(src, outdir, " (images)")
            n += 1
            (folder / f"image-{n:03d}.{data['ext']}").write_bytes(data["image"])
    doc.close()
    if not folder:
        raise ConvertError("No embedded images found")
    return [folder]
