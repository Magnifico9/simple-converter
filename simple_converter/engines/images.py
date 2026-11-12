from pathlib import Path

from PIL import Image, ImageOps, ImageSequence

from ..util import ConvertError, out_path

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:  # pragma: no cover
    pillow_heif = None

PIL_FMT = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "avif": "AVIF", "bmp": "BMP",
           "tiff": "TIFF", "gif": "GIF", "ico": "ICO", "pdf": "PDF", "heic": "HEIF"}
EXIF_OK = {"jpg", "webp", "png", "tiff", "avif", "heic"}
ANIM_OK = {"gif", "webp", "png", "avif"}


def open_image(src: Path, svg_width: int | None = None) -> Image.Image:
    if src.suffix.lower() == ".svg":
        import pymupdf as fitz
        doc = fitz.open(src)
        page = doc[0]
        w = page.rect.width or 512
        target = svg_width or max(1024, int(w))
        pix = page.get_pixmap(matrix=fitz.Matrix(target / w, target / w), alpha=True)
        im = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
        doc.close()
        return im
    try:
        im = Image.open(src)
        im.load()
    except Exception as e:
        raise ConvertError(f"Can't open image: {e}")
    return im


def _flatten(im: Image.Image, bg=(255, 255, 255)) -> Image.Image:
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        base = Image.new("RGB", im.size, bg)
        base.paste(im, mask=im.getchannel("A"))
        return base
    return im.convert("RGB")


def _prepare(im: Image.Image, fmt: str) -> Image.Image:
    if im.mode == "CMYK" and fmt != "jpg":
        im = im.convert("RGB")
    if im.mode in ("I;16", "I", "F") and fmt not in ("png", "tiff"):
        im = im.convert("I").point(lambda x: x / 256).convert("L")
    if fmt in ("jpg", "pdf"):
        return _flatten(im)
    if fmt == "bmp":
        return im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") and _has_alpha(im) else im.convert("RGB")
    if fmt in ("webp", "avif", "heic"):
        return im.convert("RGBA") if _has_alpha(im) else im.convert("RGB")
    if fmt == "ico":
        return im.convert("RGBA")
    if fmt == "png" and im.mode not in ("1", "L", "LA", "P", "RGB", "RGBA", "I;16"):
        return im.convert("RGBA")
    return im


def _has_alpha(im):
    return im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)


def apply_ops(im: Image.Image, opts: dict) -> Image.Image:
    if not getattr(im, "is_animated", False):
        im = ImageOps.exif_transpose(im)
    pct = opts.get("resize_pct")
    w, h = opts.get("width"), opts.get("height")
    if pct and pct != 100:
        im = im.resize((max(1, round(im.width * pct / 100)), max(1, round(im.height * pct / 100))),
                       Image.LANCZOS)
    elif w or h:
        if w and h and opts.get("keep_ratio", True):
            im = ImageOps.contain(im, (int(w), int(h)), Image.LANCZOS)
        elif w and h:
            im = im.resize((int(w), int(h)), Image.LANCZOS)
        elif w:
            im = im.resize((int(w), max(1, round(im.height * int(w) / im.width))), Image.LANCZOS)
        else:
            im = im.resize((max(1, round(im.width * int(h) / im.height)), int(h)), Image.LANCZOS)
    rot = int(opts.get("rotate") or 0)
    if rot:
        im = im.rotate(-rot, expand=True)
    if opts.get("grayscale"):
        im = ImageOps.grayscale(im) if not _has_alpha(im) else \
            Image.merge("LA", (ImageOps.grayscale(im.convert("RGB")), im.convert("RGBA").getchannel("A")))
    return im


def save_image(im: Image.Image, dst: Path, fmt: str, opts: dict, src_info: dict):
    q = int(opts.get("quality") or (90 if fmt in ("jpg", "heic") else 85))
    kw = {}
    exif = None if opts.get("strip") else src_info.get("exif")
    if exif and fmt in EXIF_OK:
        kw["exif"] = exif
    icc = src_info.get("icc_profile")
    if icc and not opts.get("strip") and fmt in ("jpg", "png", "webp", "tiff", "avif"):
        kw["icc_profile"] = icc
    if fmt == "jpg":
        kw.update(quality=q, optimize=True, progressive=True, subsampling="4:2:0" if q < 90 else 0)
    elif fmt in ("webp", "avif", "heic"):
        kw.update(quality=q)
        if fmt == "webp":
            kw["method"] = 6
    elif fmt == "png":
        kw["optimize"] = True
    elif fmt == "tiff":
        kw["compression"] = "tiff_lzw"
    elif fmt == "ico":
        side = min(256, max(im.size))
        kw["sizes"] = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256) if s <= side] or [(side, side)]
        if im.width != im.height:  # pad to square so the icon isn't squashed
            sq = Image.new("RGBA", (max(im.size),) * 2, (0, 0, 0, 0))
            sq.paste(im, ((sq.width - im.width) // 2, (sq.height - im.height) // 2))
            im = sq
    elif fmt == "pdf":
        kw["resolution"] = 150
    try:
        im.save(dst, PIL_FMT[fmt], **kw)
    except Exception as e:
        if dst.exists():
            dst.unlink()
        raise ConvertError(f"Can't save {fmt.upper()}: {e}")


def convert(src: Path, to: str, outdir=None, opts=None, suffix="") -> list[Path]:
    opts = opts or {}
    im = open_image(src, svg_width=opts.get("width"))
    info = dict(im.info)
    dst = out_path(src, outdir, to, suffix)
    # keep animation (gif -> webp etc.) when nothing changes the frames
    if getattr(im, "is_animated", False) and to in ANIM_OK and not _frame_ops(opts):
        frames = [_prepare(f.copy(), to) for f in ImageSequence.Iterator(im)]
        kw = {"save_all": True, "append_images": frames[1:],
              "duration": info.get("duration", 100), "loop": info.get("loop", 0)}
        if to in ("webp", "avif"):
            kw["quality"] = int(opts.get("quality") or 85)
        frames[0].save(dst, PIL_FMT[to], **kw)
        return [dst]
    im = apply_ops(im, opts)
    save_image(_prepare(im, to), dst, to, opts, info)
    return [dst]


def _frame_ops(opts):
    return bool((opts.get("resize_pct") or 100) != 100 or opts.get("width") or opts.get("height")
                or opts.get("rotate") or opts.get("grayscale"))


def same_format(src: Path) -> str:
    from ..formats import ext_of
    e = ext_of(src)
    return e if e in PIL_FMT and e != "pdf" else "jpg"


def compress(src: Path, outdir=None, opts=None) -> list[Path]:
    fmt = same_format(src)
    if fmt in ("heic", "bmp", "tiff"):
        fmt = "jpg"
    im = open_image(src)
    info = dict(im.info)
    im = ImageOps.exif_transpose(im)
    dst = out_path(src, outdir, fmt, " (compressed)")
    if fmt == "png":
        im = im.convert("RGBA") if _has_alpha(im) else im.convert("RGB")
        im = im.quantize(256, method=Image.Quantize.FASTOCTREE if im.mode == "RGBA" else Image.Quantize.MEDIANCUT,
                         dither=Image.Dither.FLOYDSTEINBERG)
        im.save(dst, "PNG", optimize=True)
    else:
        save_image(_prepare(im, fmt), dst, fmt, {"quality": 70}, info)
    return [dst]


def tool(src: Path, kind: str, outdir=None) -> list[Path]:
    fmt = same_format(src)
    if kind == "resize":
        return convert(src, fmt, outdir, {"resize_pct": 50}, " (50%)")
    if kind == "rotate":
        return convert(src, fmt, outdir, {"rotate": 90}, " (rotated)")
    if kind == "strip":
        return convert(src, fmt, outdir, {"strip": True, "quality": 95}, " (no metadata)")
    raise ConvertError(kind)


def combine_pdf(files: list[Path], outdir=None) -> list[Path]:
    pages = []
    for f in files:
        im = apply_ops(open_image(f), {})
        pages.append(_flatten(im))
    if not pages:
        return []
    d = outdir or files[0].parent
    dst = out_path(Path(d) / "Combined images.pdf", outdir, "pdf")
    pages[0].save(dst, "PDF", resolution=150, save_all=True, append_images=pages[1:])
    return [dst]
