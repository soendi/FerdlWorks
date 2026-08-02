import os
import random
import winsound

_SOUND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
_WAV_PATH = os.path.join(_SOUND_DIR, "signaturesound.wav")
_OGG_PATH = os.path.join(_SOUND_DIR, "signaturesound.ogg")

_next_timer = None


def _play():
    if os.path.exists(_WAV_PATH):
        winsound.PlaySound(_WAV_PATH, winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_NODEFAULT)


def _schedule(master, db):
    global _next_timer
    delay = random.randint(270, 330) * 1000
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
