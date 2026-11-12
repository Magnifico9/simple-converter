"""Script install (used by install.bat / uninstall.bat).

    python install.py            install or refresh (asks for admin once)
    python install.py --remove   uninstall
    python install.py --user     per-user only, no admin (some Windows 11 builds ignore it)

The SimpleConverter-Setup.exe installer does the same thing for the bundled app.
"""
import ctypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from simple_converter import registry  # noqa: E402
from simple_converter.util import ICON  # noqa: E402

MACHINE = "--user" not in sys.argv


def pythonw() -> str:
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w if w.exists() else exe)


if __name__ == "__main__":
    if MACHINE and not registry.is_admin():
        # relaunch elevated (one UAC prompt); the new window shows the result
        args = " ".join(f'"{a}"' for a in [__file__, *sys.argv[1:], "--pause"])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, str(ROOT), 1)
        if rc <= 32:
            print("Administrator permission is needed to add the menu for all file types.")
        sys.exit(0)
    if "--remove" in sys.argv:
        registry.unregister()
    else:
        registry.make_icon()
        registry.register(f'"{pythonw()}" "{ROOT / "launcher.pyw"}"', str(ICON), machine=MACHINE)
    if "--pause" in sys.argv:
        input("\nPress Enter to close...")
