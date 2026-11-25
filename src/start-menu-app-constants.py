import os
import gettext
import locale

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

IGNORED_CATEGORIES = {
    "xfce",
    "x-xfce",
    "x-xfce-settingsdialog",
    "x-xfce-personalsettings",
    "x-xfce-hardwaresettings",
    "x-xfce-systemsettings",
    "x-xfce-toplevel",
    "gnome",
    "kde",
    "mate",
    "lxde",
    "lxqt",
    "cinnamon",
    "pantheon",
    "gtk",
    "qt",
    "motif",
    "java",
    "consoleonly",
    "application",
    "core",
    "x-red-hat-base",
    "x-suse-core-system",
    "x-debian-applications",
}

FIXED_CATEGORIES = [
    (
        "Terminal",
        {
            "terminalemulator",
            "x-debug-applications-shell",
            "x-debian-applications-shell",
            "x-debian-applications-shells",
        },
    ),
    (
        "Development",
        {
            "development",
            "ide",
            "debugger",
            "revisioncontrol",
            "profiling",
            "translation",
            "guidesigner",
            "database",
            "webdevelopment",
        },
    ),
    (
        "Games",
        {
            "game",
            "actiongame",
            "adventuregame",
            "arcadegame",
            "boardgame",
            "cardgame",
            "logicgame",
            "roleplaying",
            "simulation",
            "sportsgame",
            "strategygame",
        },
    ),
    (
        "Graphics & Design",
        {
            "graphics",
            "2dgraphics",
            "3dgraphics",
            "vectorgraphics",
            "rastergraphics",
            "photography",
            "scanning",
            "publishing",
        },
    ),
    (
        "Multimedia",
        {
            "audiovideo",
            "audio",
            "video",
            "player",
            "recorder",
            "midi",
            "mixer",
            "sequencer",
            "tuner",
            "tv",
            "discburning",
        },
    ),
    (
        "Internet & Network",
        {
            "network",
            "webbrowser",
            "email",
            "instantmessaging",
            "filetransfer",
            "remoteaccess",
            "p2p",
            "ircclient",
            "news",
        },
    ),
    (
        "Office & Productivity",
        {
            "office",
            "wordprocessor",
            "spreadsheet",
            "presentation",
            "calendar",
            "contactmanagement",
            "viewer",
            "texteditor",
            "finance",
            "projectmanagement",
        },
    ),
    (
        "Education & Science",
        {
            "education",
            "science",
            "math",
            "astronomy",
            "biology",
            "chemistry",
            "physics",
            "engineering",
            "electronics",
            "geography",
            "languages",
        },
    ),
    (
        "System",
        {
            "system",
            "monitor",
            "packagemanager",
            "filesystem",
            "security",
            "emulator",
            "settings",
            "hardwaresettings",
            "desktopsettings",
        },
    ),
    (
        "Utilities",
        {
            "utility",
            "archiving",
            "compression",
            "filetools",
            "filemanager",
            "calculator",
            "clock",
            "accessibility",
            "texttools",
        },
    ),
    ("Other", set()),
]

CATEGORY_NAMES = [name for name, _ in FIXED_CATEGORIES]

APP_CSS = b"""
window {
    border: 1px solid @borders;
}
.section-title {
    font-weight: bold;
    font-size: 1.05em;
}
.section-header-btn {
    padding: 2px 6px;
    border-radius: 6px;
}
.view-btn {
    padding: 2px 8px;
}
.cat-card {
    background-color: alpha(@theme_fg_color, 0.04);
    border: 1px solid alpha(@borders, 0.5);
    border-radius: 10px;
    padding: 10px;
}
.cat-card:hover {
    background-color: alpha(@theme_fg_color, 0.09);
}
flowboxchild {
    padding: 0;
    margin: 0;
}
button.pinned-item, button.grid-item {
    border-radius: 8px;
    min-width: 0;
    min-height: 0;
    margin: 0;
}
button.pinned-item:hover, button.grid-item:hover {
    background-color: alpha(@theme_fg_color, 0.08);
}
.pinned-drop-target {
    border: 1px dashed @theme_selected_bg_color;
    background-color: alpha(@theme_selected_bg_color, 0.15);
}
"""

ICON_SIZE_PRESETS = [
    ("small", _("Small"), 24),
    ("normal", _("Normal"), 32),
    ("large", _("Large"), 40),
    ("huge", _("Huge"), 48),
]

# Значения: (padding_v, padding_h, flowbox_gap, vbox_spacing, max_chars, max_cols)
# Значения: (padding_v, padding_h, flowbox_gap, vbox_spacing, max_chars, max_cols)
TILE_PADDING_PRESETS = [
    ("tight", _("Tight"), (1, 1, 1, 1, 7, 12)),
    ("normal", _("Normal"), (3, 2, 3, 2, 8, 10)),
    ("relaxed", _("Relaxed"), (5, 4, 6, 3, 9, 9)),
    ("wide", _("Wide"), (7, 5, 10, 4, 10, 8)),
]

LABEL_SIZE_PRESETS = [
    ("small", _("Small"), "0.78em"),
    ("normal", _("Normal"), "0.90em"),
    ("large", _("Large"), "1.05em"),
    ("huge", _("Huge"), "1.18em"),
]
