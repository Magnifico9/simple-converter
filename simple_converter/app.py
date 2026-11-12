import argparse
import os
from pathlib import Path

from . import batching, jobs, notify
from .util import LOG, log, natural_key

OP_NAMES = {
    "img_compress": "Compressing", "img_resize": "Resizing", "img_rotate": "Rotating",
    "img_strip": "Removing metadata from", "img_combine_pdf": "Combining",
    "vid_compress": "Compressing", "vid_mute": "Removing audio from", "vid_frame": "Grabbing a frame from",
    "aud_compress": "Compressing", "aud_normalize": "Normalizing",
    "pdf_merge": "Merging", "pdf_split": "Splitting", "pdf_compress": "Compressing",
    "pdf_images": "Extracting images from", "pres_images": "Exporting slides from",
}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="simple_converter")
    ap.add_argument("--op", required=True)
    ap.add_argument("--to", default="")
    ap.add_argument("--no-batch", action="store_true", help="don't wait for other selected files")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)

    files = a.files
    if not a.no_batch:
        files = batching.collect(f"{a.op}_{a.to}", files)
        if not files:
            return 0
    paths = sorted({Path(f) for f in files if os.path.exists(f)},
                   key=lambda p: (natural_key(p.parent), natural_key(p.stem), p.suffix.lower()))
    if not paths:
        return 0

    op, to, opts = a.op, a.to, {}
    if op == "advanced":
        from . import advanced
        res = advanced.ask(paths)
        if not res:
            return 0
        op, to, opts = "convert", res["to"], res["opts"]

    what = f"{len(paths)} files" if len(paths) > 1 else paths[0].name
    verb = OP_NAMES.get(op, "Converting")
    target = f" to {to.upper()}" if op == "convert" else ""
    log(f"START op={op} to={to} opts={opts} files={[str(p) for p in paths]}")
    if jobs.is_slow(op, to, paths):
        notify.toast(f"{verb} {what}{target}…", "You'll get a notification when it's done.")

    outputs, errors = jobs.run(op, to, paths, opts)
    log(f"DONE outputs={[str(o) for o in outputs]} errors={errors}")

    folder = str((outputs[0].parent if outputs[0].is_file() else outputs[0]) if outputs else paths[0].parent)
    if errors and not outputs:
        first = errors[0]
        name = first[0].name + ": " if first[0] else ""
        notify.toast("Conversion failed", f"{name}{first[1]}", launch=str(LOG))
        if len(errors) > 1 or len(first[1]) > 120:
            notify.error_box("Simple Converter – conversion failed",
                             "\n\n".join(f"{e[0].name if e[0] else 'Batch'}: {e[1]}" for e in errors[:10]))
        return 1
    if errors:
        notify.toast(f"Done with {len(errors)} error(s)",
                     f"{len(outputs)} created. First error – {errors[0][0].name if errors[0][0] else ''}: "
                     f"{errors[0][1]}", launch=folder)
        return 1
    made = outputs[0].name if len(outputs) == 1 else f"{len(outputs)} files"
    notify.toast("Done ✓", f"Created {made}", launch=folder)
    return 0
