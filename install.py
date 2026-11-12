"""Add / remove the 'Convert to' right-click menu (current user only, no admin).

    python install.py            install or refresh
    python install.py --remove   uninstall
"""
import ctypes
import sys
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from simple_converter import tools  # noqa: E402
from simple_converter.formats import EXT_FAMILY, menu_for  # noqa: E402
from simple_converter.util import ICON  # noqa: E402

HKCU = winreg.HKEY_CURRENT_USER
# Menu entries go machine-wide (HKLM): on some Windows 11 builds Explorer
# ignores per-user (HKCU) shell verbs. Needs admin; use --user to force HKCU.
MENU_ROOT = HKCU if "--user" in sys.argv else winreg.HKEY_LOCAL_MACHINE
SFA = r"Software\Classes\SystemFileAssociations"
VERB = "SimpleConverter"
AUMID = r"Software\Classes\AppUserModelId\SimpleConverter"
LEGACY_VERBS = ["Convertool"]  # earlier names, cleaned up on install/remove
LEGACY_AUMIDS = [r"Software\Classes\AppUserModelId\Convertool"]
SEPARATOR_BEFORE = 0x20


def make_icon():
    from PIL import Image, ImageDraw
    ICON.parent.mkdir(exist_ok=True)
    S = 256
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, S - 8, S - 8), radius=56, fill=(91, 76, 230))
    d.rounded_rectangle((8, 8, S - 8, S // 2), radius=56, fill=(120, 104, 255))
    d.rectangle((8, S // 2 - 40, S - 8, S // 2), fill=(120, 104, 255))
    w = (255, 255, 255)
    # top arrow ->
    d.rounded_rectangle((52, 78, 170, 104), radius=12, fill=w)
    d.polygon([(160, 50), (212, 91), (160, 132)], fill=w)
    # bottom arrow <-
    d.rounded_rectangle((86, 152, 204, 178), radius=12, fill=w)
    d.polygon([(96, 124), (44, 165), (96, 206)], fill=w)
    im.save(ICON, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def pythonw() -> str:
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w if w.exists() else exe)


def _delete_tree(root, path):
    try:
        with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as k:
            while True:
                try:
                    sub = winreg.EnumKey(k, 0)
                except OSError:
                    break
                _delete_tree(root, path + "\\" + sub)
        winreg.DeleteKey(root, path)
    except (FileNotFoundError, PermissionError):
        pass


def _set(key, name, value, kind=winreg.REG_SZ):
    winreg.SetValueEx(key, name, 0, kind, value)


def notify_shell():
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def clean():
    """Delete current and older menu entries from both per-user and machine locations."""
    for ext in EXT_FAMILY:
        for root in (HKCU, winreg.HKEY_LOCAL_MACHINE):
            for verb in [VERB, *LEGACY_VERBS]:
                _delete_tree(root, rf"{SFA}\.{ext}\shell\{verb}")
    for key in [AUMID, *LEGACY_AUMIDS]:
        _delete_tree(HKCU, key)


def remove():
    clean()
    notify_shell()
    print("Removed the Convert menu.")


def install():
    make_icon()
    avail = tools.available()
    print("Found tools:", ", ".join(sorted(avail)) or "none")
    for name, nice in (("ffmpeg", "FFmpeg (video/audio)"), ("soffice", "LibreOffice (Office docs)"),
                       ("calibre", "Calibre (ebooks)")):
        if name not in avail:
            print(f"  ! {nice} not found - those conversions are hidden. Re-run install after installing it.")

    clean()  # start clean so removed items and old names disappear

    pyw, launcher, icon = pythonw(), str(ROOT / "launcher.pyw"), str(ICON)
    count = 0
    for ext in EXT_FAMILY:
        items = menu_for(ext, avail)
        if not items:
            continue
        base = rf"{SFA}\.{ext}\shell\{VERB}"
        with winreg.CreateKey(MENU_ROOT, base) as k:
            _set(k, "MUIVerb", "Convert to")
            _set(k, "Icon", icon)
            _set(k, "SubCommands", "")
            _set(k, "MultiSelectModel", "Player")
        for it in items:
            sub = rf"{base}\shell\{it['key']}"
            with winreg.CreateKey(MENU_ROOT, sub) as k:
                _set(k, "MUIVerb", it["label"])
                _set(k, "MultiSelectModel", "Player")
                if it["sep"]:
                    _set(k, "CommandFlags", SEPARATOR_BEFORE, winreg.REG_DWORD)
            args = f'--op {it["op"]}' + (f' --to {it["to"]}' if it["to"] else "")
            with winreg.CreateKey(MENU_ROOT, sub + r"\command") as k:
                _set(k, "", f'"{pyw}" "{launcher}" {args} "%1"')
        count += 1

    # lets Windows show our toast notifications with a name and icon
    with winreg.CreateKey(HKCU, AUMID) as k:
        _set(k, "DisplayName", "Simple Converter")
        _set(k, "IconUri", icon)
        _set(k, "ShowInSettings", 0, winreg.REG_DWORD)

    notify_shell()
    print(f"Installed 'Convert to' menu for {count} file types.")


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


if __name__ == "__main__":
    if MENU_ROOT != HKCU and not is_admin():
        # relaunch elevated (one UAC prompt); the new window shows the result
        args = " ".join(f'"{a}"' for a in [__file__, *sys.argv[1:], "--pause"])
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, str(ROOT), 1)
        if rc <= 32:
            print("Administrator permission is needed to add the menu for all file types.")
        sys.exit(0)
    remove() if "--remove" in sys.argv else install()
    if "--pause" in sys.argv:
        input("\nPress Enter to close...")
