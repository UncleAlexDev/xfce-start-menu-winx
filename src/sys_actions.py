import shlex
import shutil
import subprocess

import gi

from sys_cmd import show_run_dialog

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

try:
    gi.require_version("Wnck", "3.0")
    from gi.repository import Wnck
except ValueError:
    Wnck = None

from sys_i18n import _


def toggle_show_desktop():
    if Wnck is None:
        return
    screen = Wnck.Screen.get_default()
    if screen is not None:
        screen.force_update()
        screen.toggle_showing_desktop(not screen.get_showing_desktop())


def run_command(cmd):
    if not cmd:
        return
    try:
        subprocess.Popen(shlex.split(cmd), start_new_session=True)
    except Exception as e:
        print(f"[xfce-start-menu] Failed to run '{cmd}': {e}")


def _show_message(msg_type, title, primary_text, secondary_text=None):
    """Показывает информационное окно или ошибку через нативный Gtk.MessageDialog."""
    dialog = Gtk.MessageDialog(
        message_type=msg_type,
        buttons=Gtk.ButtonsType.OK,
        text=primary_text,
    )
    dialog.set_title(title)
    if secondary_text:
        dialog.format_secondary_text(secondary_text)
    dialog.run()
    dialog.destroy()


def _ask_and_install(binary, pkg):
    """Спрашивает подтверждение через Gtk.MessageDialog и запускает установку в терминале."""
    q_text = _(
        "Application '{bin}' is not installed.\nInstall package '{pkg}' now?"
    ).format(bin=binary, pkg=pkg)

    dialog = Gtk.MessageDialog(
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.YES_NO,
        text=q_text,
    )
    dialog.set_title(_("System Menu"))
    response = dialog.run()
    dialog.destroy()

    if response == Gtk.ResponseType.YES:
        msg_ok = _("Installation complete. You can close this terminal.")
        msg_err = _("Installation failed! You can close this terminal.")
        apt_cmd = (
            f"if sudo apt update && sudo apt install -y {shlex.quote(pkg)}; then "
            f"printf '\\n----------------------------------------\\n%s\\n' {shlex.quote(msg_ok)}; "
            f"else "
            f"printf '\\n----------------------------------------\\n%s\\n' {shlex.quote(msg_err)}; "
            f"fi"
        )
        term_cmd = f"sh -c {shlex.quote(apt_cmd)}"
        run_command(f"xfce4-terminal --hold -e {shlex.quote(term_cmd)}")


# System menu command mapping:
#   key: (command_or_callable, apt_package_name_or_None)
# Tuple is used because the executable name or command with arguments
# often differs from the Debian/APT package name (e.g. 'gnome-disks' -> 'gnome-disk-utility').
# fmt: off
WINX_COMMANDS = {
    "installed_apps":   (None, None),
    "power":            ("xfce4-power-manager-settings", "xfce4-power-manager"),
    "event_viewer":     (None, None),
    "system":           ("hardinfo2", "hardinfo2"),
    "device_manager":   (None, None),
    "network":          ("nm-connection-editor", "network-manager-gnome"),
    "disks":            ("gnome-disks", "gnome-disk-utility"),
    "computer_mgmt":    (None, None),
    "terminal":         ("xfce4-terminal", "xfce4-terminal"),
    "terminal_admin":   (
        'sh -c \'pkexec env DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" xfce4-terminal\'',
        "xfce4-terminal",
    ),
    "task_manager":     ("xfce4-taskmanager", "xfce4-taskmanager"),
    "settings":         ("xfce4-settings-manager", "xfce4-settings"),
    "file_explorer":    ("thunar", "thunar"),
    "search":           ("xfce4-appfinder", "xfce4-appfinder"),
    "run":              (show_run_dialog, None),
    "logout":           ("xfce4-session-logout --logout", "xfce4-session"),
    "suspend":          ("xfce4-session-logout --suspend", "xfce4-session"),
    "hibernate":        ("xfce4-session-logout --hibernate", "xfce4-session"),
    "halt":             ("xfce4-session-logout --halt", "xfce4-session"),
    "reboot":           ("xfce4-session-logout --reboot", "xfce4-session"),
    "desktop":          (toggle_show_desktop, None),
}
# fmt: on


def resolve_action(cmd_key):
    cmd, pkg = WINX_COMMANDS.get(cmd_key, (None, None))

    if not cmd:
        msg = _("No suitable application.\nUnder developing...")
        return " [X]", lambda: _show_message(Gtk.MessageType.INFO, _("System Menu"), msg)

    if callable(cmd):
        return "", cmd

    binary = shlex.split(cmd)[0]
    if shutil.which(binary) is not None:
        return "", cmd

    if pkg:
        return " [!]", lambda b=binary, p=pkg: _ask_and_install(b, p)

    err_text = _("Command '{bin}' not found.").format(bin=binary)
    return " [?]", lambda: _show_message(Gtk.MessageType.ERROR, _("System Menu"), err_text)

def execute_winx_key(cmd_key, anchor=None):
    """Универсальный запуск любого пункта WINX_COMMANDS по его ключу."""
    if cmd_key not in WINX_COMMANDS:
        return False
    if cmd_key == "run":
        show_run_dialog(anchor)
        return True
    _, action = resolve_action(cmd_key)
    if callable(action):
        action()
    else:
        run_command(action)
    return True

