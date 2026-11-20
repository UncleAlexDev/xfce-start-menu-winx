import gettext
import locale
import os

APP_DOMAIN = "xfce-start-menu"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_LOCALE_DIR = os.path.join(BASE_DIR, "locale")
SYS_LOCALE_DIR = "/usr/share/locale"

LOCALE_DIR = LOCAL_LOCALE_DIR if os.path.isdir(LOCAL_LOCALE_DIR) else SYS_LOCALE_DIR

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

_translation = gettext.translation(APP_DOMAIN, localedir=LOCALE_DIR, fallback=True)
_ = _translation.gettext


def get_version():
    ver_file = os.path.join(BASE_DIR, "VERSION")
    try:
        with open(ver_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


APP_VERSION = get_version()
