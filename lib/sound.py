import os
import sys
import random
import winsound

_WAV_PATH = None


def _find_wav():
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "signaturesound.wav"),
    ]
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        candidates += [
            os.path.join(base, "assets", "signaturesound.wav"),
            os.path.join(base, "_internal", "assets", "signaturesound.wav"),
            os.path.join(base, "_internal", "signaturesound.wav"),
        ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


_next_timer = None


def _play():
    global _WAV_PATH
    if _WAV_PATH is None:
        _WAV_PATH = _find_wav()
    if _WAV_PATH and os.path.exists(_WAV_PATH):
        winsound.PlaySound(_WAV_PATH, winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        _log("Köppel sound abgespielt: " + _WAV_PATH)
    else:
        _log("Köppel sound: WAV nicht gefunden")


def _log(msg):
    try:
        from lib.logger import get_logger
        get_logger().info(msg)
    except Exception:
        pass


def _schedule(master, db):
    global _next_timer
    delay = random.randint(240, 300) * 1000
    _log(f"Köppel sound: naechster in {delay//1000}s")
    def _tick():
        global _next_timer
        _next_timer = None
        try:
            settings = db.settings_get_all()
            if settings.get("koeppel_sound", "1") == "1":
                _play()
        except Exception:
            pass
        _schedule(master, db)
    _next_timer = master.after(delay, _tick)


def start_timer(master, db):
    _schedule(master, db)


def stop_timer(master):
    global _next_timer
    if _next_timer is not None:
        try:
            master.after_cancel(_next_timer)
        except Exception:
            pass
        _next_timer = None
