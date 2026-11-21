import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from sys_i18n import _

# Единый эталонный реестр глобальных хоткеев плагина (Single Source of Truth):
# event_name: (xfce_accel, conflicting_xfconf_paths)
# fmt: off
DEFAULT_SHORTCUTS = {
    "start":         ("Super_L", []),
    "winx":          ("<Super>x", []),
    "settings":      ("<Super>i", ["/commands/default/<Super>i", "/commands/custom/<Super>I"]),
    "file_explorer": ("<Super>e", ["/commands/default/<Super>e"]),
    "search":        ("<Super>s", ["/commands/default/<Super>s"]),
    "run":           ("<Super>r", ["/commands/default/<Super>r"]),
    "task_manager":  ("<Primary><Shift>Escape", ["/commands/default/<Primary><Shift>Escape"]),
    "desktop":       ("<Super>d", ["/commands/default/<Super>d"]),
}
# fmt: on

_user_dismissed_drift = False


def _xfconf_get(channel, prop_path):
    try:
        res = subprocess.run(
            ["xfconf-query", "-c", channel, "-p", prop_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except OSError:
        pass
    return None


def _xfconf_reset(channel, prop_path):
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


def _humanize_accel(accel):
    """Преобразует XFCE-строку вида '<Super>i' в читаемый вид 'Win+I'."""
    if not accel:
        return ""
    formatted = (
        accel.replace("<Super>", "Win+")
        .replace("<Primary>", "Ctrl+")
        .replace("<Control>", "Ctrl+")
        .replace("<Alt>", "Alt+")
        .replace("<Shift>", "Shift+")
        .replace("Super_L", "Win")
        .replace("Escape", "Esc")
    )
    if "+" in formatted:
        prefix, key = formatted.rsplit("+", 1)
        if len(key) == 1:
            formatted = f"{prefix}+{key.upper()}"
    return formatted


def check_shortcuts_drift(plugin_name="start-menu", shortcuts_map=None):
    """Возвращает список несоответствий между эталоном и реальным xfconf."""
    if shortcuts_map is None:
        shortcuts_map = DEFAULT_SHORTCUTS

    issues = []
    for event_name, (accel, conflicts) in shortcuts_map.items():
        if not accel:
            continue
        human_accel = _humanize_accel(accel)
        expected_cmd = f"xfce4-panel --plugin-event={plugin_name}:{event_name}:bool:true"
        actual_cmd = _xfconf_get("xfce4-keyboard-shortcuts", f"/commands/custom/{accel}")
        if actual_cmd != expected_cmd:
            issues.append(f"• {human_accel}: '{actual_cmd or 'None'}' → '{event_name}'")

        custom_conflicts = [p for p in conflicts if "/custom/" in p] + [f"/xfwm4/custom/{accel}"]
        for path in custom_conflicts:
            if _xfconf_get("xfce4-keyboard-shortcuts", path) is not None:
                issues.append(f"• {human_accel}: conflict at {path}")
    return issues


def sync_plugin_shortcuts(plugin_name="start-menu", shortcuts_map=None):
    """Принудительно записывает эталонные хоткеи плагина и удаляет конфликты в custom-ветках."""
    if shortcuts_map is None:
        shortcuts_map = DEFAULT_SHORTCUTS

    for event_name, (accel, conflicts) in shortcuts_map.items():
        if not accel:
            continue
        custom_conflicts = [p for p in conflicts if "/custom/" in p] + [f"/xfwm4/custom/{accel}"]
        for path in custom_conflicts:
            _xfconf_reset("xfce4-keyboard-shortcuts", path)
        cmd = f"xfce4-panel --plugin-event={plugin_name}:{event_name}:bool:true"
        _xfconf_set("xfce4-keyboard-shortcuts", f"/commands/custom/{accel}", cmd)


def ensure_plugin_shortcuts(plugin_name="start-menu", interactive=True):
    """Проверяет хоткеи и при расхождении предлагает пользователю исправить их."""
    global _user_dismissed_drift
    if _user_dismissed_drift:
        return True

    issues = check_shortcuts_drift(plugin_name)
    if not issues:
        return True

    if not interactive:
        sync_plugin_shortcuts(plugin_name)
        return True

    dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.NONE,
        text=_("Keyboard shortcuts mismatch detected for Xfce Start Menu."),
    )
    dialog.set_title(_("System Menu"))
    secondary = (
        _(
            "Fix incompatible shortcuts now?\n"
            "If left as is, system menu hotkeys may work unstably.\n"
            "You can also review them manually in: Settings → Keyboard → Application Shortcuts.\n\n"
        )
        + "\n".join(issues[:8])
    )
    dialog.format_secondary_text(secondary)
    dialog.add_button(_("Leave as is"), Gtk.ResponseType.CANCEL)
    dialog.add_button(_("Open Keyboard..."), Gtk.ResponseType.HELP)
    fix_btn = dialog.add_button(_("Fix now"), Gtk.ResponseType.OK)
    fix_btn.get_style_context().add_class("suggested-action")
    dialog.set_default_response(Gtk.ResponseType.OK)

    response = dialog.run()
    dialog.destroy()

    if response == Gtk.ResponseType.OK:
        sync_plugin_shortcuts(plugin_name)
        return True

    if response == Gtk.ResponseType.HELP:
        try:
            subprocess.Popen(["xfce4-keyboard-settings"], start_new_session=True)
        except OSError:
            pass
        return False

    if response == Gtk.ResponseType.CANCEL:
        _user_dismissed_drift = True

    return False

