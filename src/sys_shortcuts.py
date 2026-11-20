import subprocess

# Единый реестр хоткеев плагина:
# event_name: (xfce_accel, conflicting_xfconf_paths)
# fmt: off
DEFAULT_SHORTCUTS = {
    "start":         ("Super_L", []),
    "winx":          ("<Super>x", []),
    "run":           ("<Super>r", ["/commands/default/<Super>r"]),
    "file_explorer": ("<Super>e", ["/commands/default/<Super>e"]),
    "settings":      ("<Super>i", ["/commands/default/<Super>i", "/commands/custom/<Super>I"]),
    "task_manager":  ("<Primary><Shift>Escape", ["/commands/default/<Primary><Shift>Escape"]),
    "desktop":       ("<Super>d", ["/commands/default/<Super>d"]),
    "terminal":      ("<Super>i", ["/commands/default/<Super>i"]),
}

# Клавиши быстрого выбора внутри открытого меню Win+X:
# event_name: (клавиша_в_нижнем_регистре, hardware_keycode_в_X11)
MENU_MNEMONICS = {
    "terminal":      ("i", 31),
}
# fmt: on

def _xfconf_reset(channel, prop_path):
    """Удаляет системный или старый хоткей, чтобы избежать конфликта."""
    try:
        subprocess.run(
            ["xfconf-query", "-c", channel, "-p", prop_path, "-r"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass


def _xfconf_set(channel, prop_path, value):
    try:
        subprocess.run(
            [
                "xfconf-query",
                "-c",
                channel,
                "-p",
                prop_path,
                "-n",
                "-t",
                "string",
                "-s",
                value,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass


def sync_plugin_shortcuts(plugin_name="start-menu", shortcuts_map=None):
    """
    Регистрирует хоткеи плагина в xfce4-keyboard-shortcuts
    и отключает конфликтующие системные привязки.
    """
    if shortcuts_map is None:
        shortcuts_map = DEFAULT_SHORTCUTS

    for event_name, (accel, conflicts) in shortcuts_map.items():
        if not accel:
            continue

        # 1. Отключаем конфликтующие системные привязки (в commands и xfwm4)
        for path in conflicts:
            _xfconf_reset("xfce4-keyboard-shortcuts", path)
        _xfconf_reset("xfce4-keyboard-shortcuts", f"/xfwm4/custom/{accel}")

        # 2. Привязываем комбинацию к remote-event нашего плагина
        # Синтаксис xfce4-panel: ИМЯ-ПЛАГИНА:ИМЯ-СОБЫТИЯ:ТИП:ЗНАЧЕНИЕ
        cmd = f"xfce4-panel --plugin-event={plugin_name}:{event_name}:bool:true"
        _xfconf_set("xfce4-keyboard-shortcuts", f"/commands/custom/{accel}", cmd)
