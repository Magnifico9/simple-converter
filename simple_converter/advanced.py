"""The 'Advanced…' dialog: pick a format plus quality / size / trim options."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from . import tools
from .formats import ext_of, family_of, targets_for
from .util import ICON

LABELS = {"jpg": "JPG", "png": "PNG", "webp": "WEBP", "avif": "AVIF", "bmp": "BMP", "tiff": "TIFF",
          "gif": "GIF", "ico": "ICO", "pdf": "PDF", "mp4": "MP4", "mkv": "MKV", "mov": "MOV",
          "avi": "AVI", "webm": "WEBM", "mp3": "MP3", "m4a": "M4A", "wav": "WAV", "flac": "FLAC",
          "ogg": "OGG", "aac": "AAC", "opus": "OPUS", "heic": "HEIC"}

QUALITY = {"High (bigger file)": 18, "Good (default)": 23, "Smaller": 28, "Smallest": 33}
SAME = "Same folder as the file"


def _dpi_aware():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def ask(files: list[Path]) -> dict | None:
    _dpi_aware()
    first = files[0]
    fam = family_of(first)
    ext = ext_of(first)
    avail = {k for k in ("ffmpeg", "soffice", "calibre", "unrar") if tools.get(k)}
    targets = targets_for(ext, avail, include_same=True)
    if not targets:
        return None

    root = tk.Tk()
    root.title("Simple Converter – Advanced")
    try:
        root.iconbitmap(str(ICON))
    except Exception:
        pass
    root.resizable(False, False)
    style = ttk.Style(root)
    try:
        style.theme_use("vista")
    except tk.TclError:
        pass
    style.configure("H.TLabel", font=("Segoe UI Semibold", 10))
    style.configure("S.TLabel", foreground="#666")

    result = {}
    frm = ttk.Frame(root, padding=16)
    frm.grid(sticky="nsew")
    r = 0

    names = ", ".join(f.name for f in files[:3]) + (f" and {len(files) - 3} more" if len(files) > 3 else "")
    ttk.Label(frm, text=names, style="H.TLabel", wraplength=420).grid(row=r, column=0, columnspan=4, sticky="w")
    r += 1
    ttk.Separator(frm).grid(row=r, column=0, columnspan=4, sticky="ew", pady=8)
    r += 1

    def label(text, row, col=0):
        ttk.Label(frm, text=text).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=3)

    def combo(values, default, row, col=1, width=22, span=1):
        v = tk.StringVar(value=default)
        ttk.Combobox(frm, textvariable=v, values=values, state="readonly", width=width) \
            .grid(row=row, column=col, columnspan=span, sticky="w", pady=3)
        return v

    def entry(row, col=1, width=10, default=""):
        v = tk.StringVar(value=default)
        ttk.Entry(frm, textvariable=v, width=width).grid(row=row, column=col, sticky="w", pady=3)
        return v

    def check(text, row, col=0, span=2):
        v = tk.BooleanVar(value=False)
        ttk.Checkbutton(frm, text=text, variable=v).grid(row=row, column=col, columnspan=span, sticky="w", pady=2)
        return v

    def section(text):
        nonlocal r
        ttk.Label(frm, text=text, style="H.TLabel").grid(row=r, column=0, columnspan=4, sticky="w", pady=(10, 2))
        r += 1

    # --- format -------------------------------------------------------------
    disp = []
    for t in targets:
        n = LABELS.get(t, t.upper())
        if t == ext or (fam == "pdf" and t == "pdf"):
            n += "  (same format, apply options)"
        disp.append(n)
    label("Convert to", r)
    fmt = combo(disp, disp[1] if len(disp) > 1 and targets[0] == ext else disp[0], r, span=3, width=34)
    r += 1

    v = {}
    if fam in ("image", "svg"):
        section("Image")
        label("Quality (1–100)", r); v["quality"] = entry(r, default="90"); r += 1
        label("Resize %", r); v["resize_pct"] = entry(r, default="100"); r += 1
        label("…or width × height (px)", r)
        wh = ttk.Frame(frm)
        wh.grid(row=r, column=1, columnspan=3, sticky="w")
        v["width"], v["height"] = tk.StringVar(), tk.StringVar()
        ttk.Entry(wh, textvariable=v["width"], width=7).pack(side="left")
        ttk.Label(wh, text=" × ").pack(side="left")
        ttk.Entry(wh, textvariable=v["height"], width=7).pack(side="left")
        r += 1
        v["keep_ratio"] = check("Keep aspect ratio", r); v["keep_ratio"].set(True); r += 1
        label("Rotate", r); v["rotate"] = combo(["0°", "90° right", "180°", "90° left"], "0°", r); r += 1
        v["grayscale"] = check("Black & white", r); r += 1
        v["strip"] = check("Remove metadata (EXIF, GPS location)", r); r += 1

    if fam == "video":
        section("Video")
        label("Resolution", r)
        v["height"] = combo(["Original", "2160p (4K)", "1440p", "1080p", "720p", "480p", "360p"], "Original", r)
        r += 1
        label("Quality", r); v["crf"] = combo(list(QUALITY), "Good (default)", r); r += 1
        label("Frame rate", r); v["fps"] = combo(["Original", "60", "30", "24", "15", "10"], "Original", r); r += 1
        label("GIF width (px)", r); v["gif_width"] = entry(r, default="480"); r += 1
        v["mute"] = check("Remove audio", r); r += 1

    if fam in ("video", "audio"):
        section("Audio")
        label("Bitrate", r)
        v["audio_bitrate"] = combo(["Auto", "320", "256", "192", "160", "128", "96", "64"], "Auto", r)
        ttk.Label(frm, text="kbps", style="S.TLabel").grid(row=r, column=2, sticky="w")
        r += 1
        label("Sample rate", r); v["sample_rate"] = combo(["Original", "48000", "44100", "22050"], "Original", r); r += 1
        label("Channels", r); v["channels"] = combo(["Original", "Stereo", "Mono"], "Original", r); r += 1
        label("Volume %", r); v["volume"] = entry(r, default="100"); r += 1
        v["normalize"] = check("Normalize loudness", r); r += 1

    if fam in ("video", "audio"):
        section("Trim")
        label("Start", r); v["start"] = entry(r)
        ttk.Label(frm, text="e.g. 1:30 or 90", style="S.TLabel").grid(row=r, column=2, columnspan=2, sticky="w")
        r += 1
        label("End", r); v["end"] = entry(r)
        ttk.Label(frm, text="leave empty = to the end", style="S.TLabel").grid(row=r, column=2, columnspan=2, sticky="w")
        r += 1

    if fam == "pdf":
        section("PDF")
        label("Pages", r); v["pages"] = entry(r, width=14)
        ttk.Label(frm, text="e.g. 1-3, 5  (empty = all)", style="S.TLabel").grid(row=r, column=2, columnspan=2, sticky="w")
        r += 1
        label("Image DPI", r); v["dpi"] = combo(["72", "100", "150", "200", "300", "600"], "150", r); r += 1
        label("Image quality", r); v["quality"] = entry(r, default="85"); r += 1
        label("Rotate pages", r); v["rotate"] = combo(["0°", "90° right", "180°", "90° left"], "0°", r); r += 1
        v["compress"] = check("Also compress (for PDF output)", r); r += 1

    # --- output folder -------------------------------------------------------
    section("Save to")
    outdir = tk.StringVar(value=SAME)
    ttk.Entry(frm, textvariable=outdir, width=36).grid(row=r, column=0, columnspan=3, sticky="ew", pady=3)

    def browse():
        d = filedialog.askdirectory(parent=root, initialdir=str(first.parent))
        if d:
            outdir.set(d)
    ttk.Button(frm, text="Browse…", command=browse).grid(row=r, column=3, sticky="e", padx=(6, 0))
    r += 1

    # --- buttons -------------------------------------------------------------
    btns = ttk.Frame(frm)
    btns.grid(row=r, column=0, columnspan=4, sticky="e", pady=(14, 0))

    def ok(*_):
        result["to"] = targets[disp.index(fmt.get())]
        o = {}
        for k, var in v.items():
            o[k] = var.get()
        result["opts"] = _clean(o)
        od = outdir.get().strip()
        if od and od != SAME:
            result["opts"]["outdir"] = od
        root.destroy()

    ttk.Button(btns, text="Convert", command=ok, default="active").pack(side="right")
    ttk.Button(btns, text="Cancel", command=root.destroy).pack(side="right", padx=6)
    root.bind("<Return>", ok)
    root.bind("<Escape>", lambda e: root.destroy())

    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.focus_force()
    root.mainloop()
    return result or None


def _num(s, cast=int):
    try:
        s = str(s).strip().rstrip("%°")
        return cast(s) if s else None
    except ValueError:
        return None


def _clean(o: dict) -> dict:
    out = {}
    for k, val in o.items():
        if isinstance(val, bool):
            if val or k == "keep_ratio":
                out[k] = val
            continue
        s = str(val).strip()
        if not s or s in ("Original", "Auto", "0°"):
            continue
        if k == "rotate":
            out[k] = {"90° right": 90, "180°": 180, "90° left": 270}.get(s, 0)
        elif k == "height":
            out[k] = _num(s.split("p")[0])
        elif k == "crf":
            out[k] = QUALITY.get(s)
        elif k == "channels":
            out[k] = 1 if s == "Mono" else 2
        elif k in ("start", "end", "pages"):
            out[k] = s
        elif k in ("fps", "volume"):
            out[k] = _num(s, float)
        else:
            out[k] = _num(s)
    if out.get("resize_pct") == 100:
        out.pop("resize_pct")
    if out.get("volume") == 100:
        out.pop("volume")
    if "gif_width" in out and out["gif_width"] == 480:
        out.pop("gif_width")
    return {k: v for k, v in out.items() if v is not None}
