"""Entry point used by the Explorer right-click menu (runs windowless)."""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# pythonw has no console; give libraries that print somewhere harmless to write
import os  # noqa: E402
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

try:
    from simple_converter.app import main
    sys.exit(main(sys.argv[1:]))
except SystemExit:
    raise
except BaseException:
    from simple_converter.util import log
    log("FATAL " + traceback.format_exc())
    try:
        from simple_converter.notify import error_box
        error_box("Simple Converter crashed",traceback.format_exc()[-1200:])
    except Exception:
        pass
    sys.exit(1)
