from .util import ICON, LOG, log

APP_ID = "SimpleConverter"


def toast(title: str, msg: str, launch: str | None = None):
    try:
        from winotify import Notification
        n = Notification(app_id=APP_ID, title=title, msg=msg[:250],
                         icon=str(ICON) if ICON.exists() else "", launch=launch or "")
        n.show()
    except Exception as e:  # never let a notification failure break a conversion
        log(f"toast failed: {e}")


def error_box(title: str, msg: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, msg[:1500] + f"\n\nLog: {LOG}", title, 0x10 | 0x40000)
    except Exception:
        pass
