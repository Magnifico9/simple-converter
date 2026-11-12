"""Which conversions are offered for which file type.

Every extension belongs to a *family*. Each family has a fixed, ordered list of
menu items. The menu for one extension is its family list minus the items that
make no sense for it (e.g. "to PNG" on a .png). Registry key names are built
from the item's position in the family list, so a mixed selection like
jpg + png still resolves the same verb name on every file.
"""

# --- canonical names -------------------------------------------------------
CANON = {
    "jpeg": "jpg", "jfif": "jpg", "jpe": "jpg",
    "tif": "tiff", "heif": "heic",
    "htm": "html", "markdown": "md", "aif": "aiff",
    "tgz": "tar.gz", "mpeg": "mpg",
}


def canon(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    return CANON.get(ext, ext)


# --- families ---------------------------------------------------------------
FAMILIES = {
    "image":    ["jpg", "jpeg", "jfif", "png", "webp", "bmp", "gif", "tif", "tiff",
                 "ico", "heic", "heif", "avif"],
    "svg":      ["svg"],
    "video":    ["mp4", "mkv", "avi", "mov", "webm", "wmv", "flv", "m4v", "3gp", "mpg", "mpeg"],
    "audio":    ["mp3", "wav", "flac", "ogg", "m4a", "aac", "wma", "opus", "aiff", "aif", "amr"],
    "subtitle": ["srt", "vtt", "ass"],
    "pdf":      ["pdf"],
    "writer":   ["doc", "docx", "odt", "rtf"],
    "calc":     ["xls", "xlsx", "ods"],
    "csv":      ["csv"],
    "json":     ["json"],
    "impress":  ["ppt", "pptx", "odp"],
    "txt":      ["txt"],
    "md":       ["md", "markdown"],
    "html":     ["html", "htm"],
    "ebook":    ["epub", "mobi", "azw3", "fb2"],
    "archive":  ["zip", "7z", "tar", "tgz", "rar"],
}

EXT_FAMILY = {e: fam for fam, exts in FAMILIES.items() for e in exts}


def family_of(path_or_ext: str) -> str | None:
    s = str(path_or_ext).lower()
    if s.endswith(".tar.gz"):
        return "archive"
    ext = s.rsplit(".", 1)[-1] if "." in s else s
    return EXT_FAMILY.get(ext)


def ext_of(path) -> str:
    s = str(path).lower()
    if s.endswith(".tar.gz"):
        return "tar.gz"
    return canon(s.rsplit(".", 1)[-1]) if "." in s else ""


# --- menu items --------------------------------------------------------------
# (op, to, label, requires, separator_before, only_for_exts)
def C(to, label=None, requires=None, sep=False, only=None):
    return {"op": "convert", "to": to, "label": label or to.upper(),
            "requires": requires, "sep": sep, "only": only}


def T(op, label, requires=None, sep=False, only=None, to=""):
    return {"op": op, "to": to, "label": label, "requires": requires, "sep": sep, "only": only}


ADV = T("advanced", "Advanced…", sep=True)

FF, LO, CAL, RAR = "ffmpeg", "soffice", "calibre", "unrar"

MENUS = {
    "image": [
        C("jpg"), C("png"), C("webp"), C("avif"), C("bmp"), C("tiff"), C("gif"),
        C("ico", "ICO (icon)"), C("pdf", "PDF"),
        C("mp4", "MP4 (video)", FF, sep=True, only=["gif"]),
        C("webm", "WEBM (video)", FF, only=["gif"]),
        T("img_compress", "Compress", sep=True),
        T("img_resize", "Resize to 50%"),
        T("img_rotate", "Rotate 90° right"),
        T("img_strip", "Remove metadata (EXIF / GPS)"),
        T("img_combine_pdf", "Combine selected into one PDF"),
        ADV,
    ],
    "svg": [C("png"), C("jpg"), C("webp"), C("ico", "ICO (icon)"), C("pdf"), ADV],
    "video": [
        C("mp4", requires=FF), C("mkv", requires=FF), C("mov", requires=FF),
        C("avi", requires=FF), C("webm", requires=FF), C("gif", "GIF (animated)", FF),
        C("mp3", "MP3 (audio only)", FF, sep=True), C("m4a", "M4A (audio only)", FF),
        C("wav", "WAV (audio only)", FF), C("flac", "FLAC (audio only)", FF),
        C("ogg", "OGG (audio only)", FF),
        T("vid_compress", "Compress (smaller file, 720p)", FF, sep=True),
        T("vid_mute", "Remove audio", FF),
        T("vid_frame", "Save a frame as image", FF),
        ADV,
    ],
    "audio": [
        C("mp3", requires=FF), C("m4a", requires=FF), C("aac", requires=FF),
        C("wav", requires=FF), C("flac", requires=FF), C("ogg", requires=FF),
        C("opus", requires=FF),
        T("aud_compress", "Compress (MP3 128 kbps)", FF, sep=True),
        T("aud_normalize", "Normalize volume", FF),
        ADV,
    ],
    "subtitle": [C("srt", requires=FF), C("vtt", requires=FF), C("ass", requires=FF)],
    "pdf": [
        C("docx", "DOCX (Word)"), C("txt", "TXT (text)"),
        C("png", "PNG (each page)"), C("jpg", "JPG (each page)"),
        C("epub", "EPUB (ebook)", CAL),
        T("pdf_merge", "Merge selected PDFs", sep=True),
        T("pdf_split", "Split into single pages"),
        T("pdf_compress", "Compress"),
        T("pdf_images", "Extract embedded images"),
        ADV,
    ],
    "writer": [
        C("pdf", requires=LO), C("docx", "DOCX (Word)", LO), C("doc", "DOC (Word 97)", LO),
        C("odt", requires=LO), C("rtf", requires=LO), C("txt", "TXT (text)", LO),
        C("html", requires=LO), C("epub", "EPUB (ebook)", LO),
        ADV,
    ],
    "calc": [
        C("pdf", requires=LO), C("xlsx", "XLSX (Excel)", LO), C("xls", "XLS (Excel 97)", LO),
        C("ods", requires=LO), C("csv"), C("json"), C("html", requires=LO),
        ADV,
    ],
    "csv": [C("xlsx", "XLSX (Excel)"), C("json"), C("ods", requires=LO), C("pdf", requires=LO)],
    "json": [C("csv"), C("xlsx", "XLSX (Excel)")],
    "impress": [
        C("pdf", requires=LO), C("pptx", "PPTX (PowerPoint)", LO),
        C("ppt", "PPT (PowerPoint 97)", LO), C("odp", requires=LO),
        T("pres_images", "Slides to PNG images", LO, sep=True),
        ADV,
    ],
    "txt": [C("pdf", requires=LO), C("docx", "DOCX (Word)", LO), C("odt", requires=LO)],
    "md": [C("html"), C("pdf", requires=LO), C("docx", "DOCX (Word)", LO)],
    "html": [C("pdf", requires=LO), C("docx", "DOCX (Word)", LO), C("txt", "TXT (text)", LO),
             C("md", "MD (Markdown)")],
    "ebook": [
        C("epub", requires=CAL), C("pdf", requires=CAL), C("mobi", requires=CAL),
        C("azw3", requires=CAL), C("docx", "DOCX (Word)", CAL), C("txt", "TXT (text)", CAL),
    ],
    "archive": [C("zip"), C("7z"), C("tar.gz", "TAR.GZ")],
}

# Families whose "Advanced…" lets you keep the same format (trim, resize, …).
SAME_FORMAT_OK = {"image", "video", "audio", "pdf"}


def menu_for(ext: str, available: set[str]) -> list[dict]:
    """Menu items for one extension, each with a stable registry key name."""
    fam = EXT_FAMILY.get(ext.lower())
    if not fam:
        return []
    c = canon(ext)
    items = []
    for idx, item in enumerate(MENUS[fam]):
        if item["requires"] and item["requires"] not in available:
            continue
        if item["only"] and c not in item["only"]:
            continue
        if item["op"] == "convert" and canon(item["to"]) == c:
            continue
        if ext == "rar" and fam == "archive" and RAR not in available:
            return []
        key = f"{idx:02d}_{item['op']}{('_' + item['to'].replace('.', '')) if item['to'] else ''}"
        items.append({**item, "key": key})
    # drop a separator flag on the very first item
    if items:
        items[0] = {**items[0], "sep": False}
    return items


def targets_for(ext: str, available: set[str], include_same=True) -> list[str]:
    """Plain conversion targets (used by the Advanced dialog)."""
    fam = EXT_FAMILY.get(ext.lower())
    if not fam:
        return []
    c = canon(ext)
    out = []
    for item in MENUS[fam]:
        if item["op"] != "convert":
            continue
        if item["requires"] and item["requires"] not in available:
            continue
        if item["only"] and c not in item["only"]:
            continue
        t = item["to"]
        if canon(t) == c and not (include_same and fam in SAME_FORMAT_OK):
            continue
        if t not in out:
            out.append(t)
    if include_same and fam in SAME_FORMAT_OK and c not in out and fam != "pdf":
        out.insert(0, c)
    if fam == "pdf" and include_same:
        out.insert(0, "pdf")
    return out
