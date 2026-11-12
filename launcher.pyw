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
    if len(sys.argv) > 1 and sys.argv[1] in ("--register", "--unregister"):
        # used by SimpleConverter-Setup.exe (bundled app), runs elevated
        from simple_converter import registry
        from simple_converter.util import log
        if sys.argv[1] == "--register":
            exe = sys.executable
            registry.register(f'"{exe}"', f'"{exe}",0', machine=True, log=log)
        else:
            registry.unregister(log=log)
        sys.exit(0)
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
