"""Register / unregister the 'Convert to' right-click menu.

Used by install.py (script install via install.bat) and by the bundled
SimpleConverter.exe (`--register` / `--unregister`, called by the Setup).
"""
import ctypes
import winreg

from . import tools
from .formats import EXT_FAMILY, menu_for
from .util import ICON

HKCU = winreg.HKEY_CURRENT_USER
HKLM = winreg.HKEY_LOCAL_MACHINE
SFA = r"Software\Classes\SystemFileAssociations"
VERB = "SimpleConverter"
AUMID = r"Software\Classes\AppUserModelId\SimpleConverter"
LEGACY_VERBS = ["Convertool"]  # earlier names, cleaned up on install/remove
LEGACY_AUMIDS = [r"Software\Classes\AppUserModelId\Convertool"]
SEPARATOR_BEFORE = 0x20


def make_icon(path=ICON):
    from PIL import Image, ImageDraw
    path.parent.mkdir(exist_ok=True)
    S = 256
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, S - 8, S - 8), radius=56, fill=(91, 76, 230))
    d.rounded_rectangle((8, 8, S - 8, S // 2), radius=56, fill=(120, 104, 255))
    d.rectangle((8, S // 2 - 40, S - 8, S // 2), fill=(120, 104, 255))
    w = (255, 255, 255)
    d.rounded_rectangle((52, 78, 170, 104), radius=12, fill=w)   # top arrow ->
    d.polygon([(160, 50), (212, 91), (160, 132)], fill=w)
    d.rounded_rectangle((86, 152, 204, 178), radius=12, fill=w)  # bottom arrow <-
    d.polygon([(96, 124), (44, 165), (96, 206)], fill=w)
    im.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


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


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def clean():
    """Delete current and older menu entries from both per-user and machine locations."""
    for ext in EXT_FAMILY:
        for root in (HKCU, HKLM):
            for verb in [VERB, *LEGACY_VERBS]:
                _delete_tree(root, rf"{SFA}\.{ext}\shell\{verb}")
    for key in [AUMID, *LEGACY_AUMIDS]:
        _delete_tree(HKCU, key)


def unregister(log=print):
    clean()
    notify_shell()
    log("Removed the Convert menu.")


def register(command: str, icon: str, machine=True, log=print) -> int:
    """command: quoted program part, e.g. '"C:\\...\\SimpleConverter.exe"'."""
    root = HKLM if machine else HKCU
    avail = tools.available()
    log("Found tools: " + (", ".join(sorted(avail)) or "none"))
    for name, nice in (("ffmpeg", "FFmpeg (video/audio)"), ("soffice", "LibreOffice (Office docs)"),
                       ("calibre", "Calibre (ebooks)")):
        if name not in avail:
            log(f"  ! {nice} not found - those conversions are hidden. Re-install after installing it.")

    clean()  # start clean so removed items and old names disappear
    count = 0
    for ext in EXT_FAMILY:
        items = menu_for(ext, avail)
        if not items:
            continue
        base = rf"{SFA}\.{ext}\shell\{VERB}"
        with winreg.CreateKey(root, base) as k:
            _set(k, "MUIVerb", "Convert to")
            _set(k, "Icon", icon)
            _set(k, "SubCommands", "")
            _set(k, "MultiSelectModel", "Player")
        for it in items:
            sub = rf"{base}\shell\{it['key']}"
            with winreg.CreateKey(root, sub) as k:
                _set(k, "MUIVerb", it["label"])
                _set(k, "MultiSelectModel", "Player")
                if it["sep"]:
                    _set(k, "CommandFlags", SEPARATOR_BEFORE, winreg.REG_DWORD)
            args = f'--op {it["op"]}' + (f' --to {it["to"]}' if it["to"] else "")
            with winreg.CreateKey(root, sub + r"\command") as k:
                _set(k, "", f'{command} {args} "%1"')
        count += 1

    # lets Windows show our toast notifications with a name and icon
    with winreg.CreateKey(HKCU, AUMID) as k:
        _set(k, "DisplayName", "Simple Converter")
        _set(k, "IconUri", icon.split(",")[0].strip('"'))
        _set(k, "ShowInSettings", 0, winreg.REG_DWORD)

    notify_shell()
    log(f"Installed 'Convert to' menu for {count} file types.")
    return count
