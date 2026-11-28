import gettext
import json
import os
import re
import shlex
import shutil
import subprocess

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Wnck", "3.0")
from gi.repository import Gtk
from gi.repository import Gtk, Wnck

from sys_cmd import show_run_dialog

try:
    _ = gettext.translation("xfce-start-menu", "/usr/share/locale").gettext
except Exception:
    _ = lambda s: s


def toggle_show_desktop():
    """Переключает режим показа рабочего стола через штатный API XFCE (Libwnck)."""
    screen = Wnck.Screen.get_default()
    if screen is None:
        return
    screen.force_update()
    screen.toggle_showing_desktop(not screen.get_showing_desktop())


def run_command(cmd):
    """Запускает внешнюю команду в фоне."""
    if not cmd:
        return
    try:
        subprocess.Popen(
            shlex.split(cmd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        _show_message(
            Gtk.MessageType.ERROR,
            _("System Menu"),
            _("Failed to execute command '{cmd}':\n{err}").format(cmd=cmd, err=e),
        )


def _show_message(msg_type, title, text):
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=msg_type,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    dialog.format_secondary_text(text)
    dialog.set_keep_above(True)
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



CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "xfce-start-menu")
WINX_COMMANDS_FILE = os.path.join(CONFIG_DIR, "winx_commands.json")

BUILTIN_HANDLERS = {
    "@builtin:run": show_run_dialog,
    "@builtin:desktop": toggle_show_desktop,
}

DEFAULT_WINX_COMMANDS = {
    "installed_apps":   {"cmd": None, "pkg": None},
    "power":            {"cmd": "xfce4-power-manager-settings", "pkg": "xfce4-power-manager"},
    "event_viewer":     {"cmd": None, "pkg": None},
    "system":           {"cmd": "hardinfo2", "pkg": "hardinfo2"},
    "device_manager":   {"cmd": None, "pkg": None},
    "network":          {"cmd": "nm-connection-editor", "pkg": "network-manager-gnome"},
    "disks":            {"cmd": "gnome-disks", "pkg": "gnome-disk-utility"},
    "computer_mgmt":    {"cmd": None, "pkg": None},
    "terminal":         {"cmd": "xfce4-terminal", "pkg": "xfce4-terminal"},
    "terminal_admin":   {
        "cmd": 'sh -c \'pkexec env DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" xfce4-terminal\'',
        "pkg": "xfce4-terminal",
    },
    "task_manager":     {"cmd": "xfce4-taskmanager", "pkg": "xfce4-taskmanager"},
    "settings":         {"cmd": "xfce4-settings-manager", "pkg": "xfce4-settings"},
    "file_explorer":    {"cmd": "thunar", "pkg": "thunar"},
    "search":           {"cmd": "xfce4-appfinder", "pkg": "xfce4-appfinder"},
    "run":              {"cmd": "@builtin:run", "pkg": None},
    "logout":           {"cmd": "xfce4-session-logout --logout", "pkg": "xfce4-session"},
    "suspend":          {"cmd": "xfce4-session-logout --suspend", "pkg": "xfce4-session"},
    "hibernate":        {"cmd": "xfce4-session-logout --hibernate", "pkg": "xfce4-session"},
    "halt":             {"cmd": "xfce4-session-logout --halt", "pkg": "xfce4-session"},
    "reboot":           {"cmd": "xfce4-session-logout --reboot", "pkg": "xfce4-session"},
    "desktop":          {"cmd": "@builtin:desktop", "pkg": None},
}


def _extract_binary(cmd):
    try:
        parts = shlex.split(cmd)
        return parts[0] if parts else None
    except ValueError:
        return None


def _is_apt_package_available(pkg_name):
    if not pkg_name or not isinstance(pkg_name, str) or not shutil.which("apt-cache"):
        return False
    try:
        res = subprocess.run(
            ["apt-cache", "show", pkg_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return res.returncode == 0
    except Exception:
        return False


def _show_fallback_dialog(title, message, default_cmd, anchor=None):
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.NONE,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.set_keep_above(True)

    has_default = bool(default_cmd)
    if has_default:
        dialog.add_button(_("Continue with\n{cmd}").format(cmd=default_cmd), Gtk.ResponseType.OK)
    dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)

    response = dialog.run()
    dialog.destroy()

    if has_default and response == Gtk.ResponseType.OK:
        if default_cmd in BUILTIN_HANDLERS:
            handler = BUILTIN_HANDLERS[default_cmd]
            show_run_dialog(anchor) if handler is show_run_dialog else handler()
        else:
            run_command(default_cmd)


def _ask_and_install_with_fallback(cmd_key, binary, pkg, default_cmd, anchor=None):
    if not _is_apt_package_available(pkg):
        msg = _(
            "Command '{bin}' is not installed on your system, and package '{pkg}' "
            "was not found in available software repositories.\n\n"
            "Check the 'cmd' and 'pkg' values for '{key}' in:\n{path}"
        ).format(bin=binary, pkg=pkg, key=cmd_key, path=WINX_COMMANDS_FILE)
        _show_fallback_dialog(_("System Menu — Configuration Error"), msg, default_cmd, anchor=anchor)
        return

    _ask_and_install(binary, pkg)


def _find_broken_json_key(raw_text, error_pos):
    """Определяет ключ верхнего уровня в JSON, внутри которого произошла синтаксическая ошибка."""
    prefix = raw_text[:error_pos]
    # Ищем все ключи вида "key_name": до места ошибки
    matches = list(re.finditer(r'"([a-zA-Z0-9_-]+)"\s*:', prefix))
    for m in reversed(matches):
        candidate = m.group(1)
        if candidate in DEFAULT_WINX_COMMANDS:
            return candidate
    return None


def _parse_valid_entries_fallback(raw_text, broken_key):
    """Извлекает валидные блоки верхнего уровня из частично повреждённого JSON."""
    recovered = {}
    for key in DEFAULT_WINX_COMMANDS:
        if key == broken_key:
            continue
        # Ищем блок "key": { ... } или "key": "..." или "key": null
        pattern = rf'"{re.escape(key)}"\s*:\s*(\{{[^{{}}]*\}}|"[^"]*"|null)'
        m = re.search(pattern, raw_text)
        if m:
            try:
                recovered[key] = json.loads(m.group(1))
            except Exception:
                pass
    return recovered


def load_winx_commands():
    commands = {k: {"cmd": v["cmd"], "pkg": v["pkg"], "error": None} for k, v in DEFAULT_WINX_COMMANDS.items()}
    cfg_hint = _("Check file:\n{path}\n\n(or delete the file to restore defaults)\n\n").format(
        path=WINX_COMMANDS_FILE
    )

    if not os.path.exists(WINX_COMMANDS_FILE):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(WINX_COMMANDS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_WINX_COMMANDS, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            print(f"[xfce-start-menu] Failed to create {WINX_COMMANDS_FILE}: {e}")
        return commands

    try:
        with open(WINX_COMMANDS_FILE, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except Exception as e:
        err_msg = _("Failed to read file:\n{path}\n\n{err}").format(path=WINX_COMMANDS_FILE, err=e)
        for k in commands:
            commands[k]["error"] = err_msg
        return commands

    broken_key = None
    syntax_err_msg = None

    try:
        user_data = json.loads(raw_text)
        if not isinstance(user_data, dict):
            raise ValueError("Root JSON element must be an object")
    except json.JSONDecodeError as e:
        broken_key = _find_broken_json_key(raw_text, e.pos)
        syntax_err_msg = _(
            "JSON syntax error in configuration file (line {line}, column {col}):\n\n{msg}\n\n{hint}"
        ).format(line=e.lineno, col=e.colno, msg=e.msg, hint=cfg_hint)
        user_data = _parse_valid_entries_fallback(raw_text, broken_key)
    except Exception as e:
        syntax_err_msg = _("Configuration error:\n{err}\n\n{hint}").format(err=e, hint=cfg_hint)
        user_data = {}

    for k, v in user_data.items():
        default_entry = DEFAULT_WINX_COMMANDS.get(k, {"cmd": None, "pkg": None})
        default_cmd = default_entry["cmd"]

        if v is None:
            commands[k] = {"cmd": None, "pkg": None, "error": None}
        elif isinstance(v, str):
            cmd_str = v.strip()
            if not cmd_str:
                commands[k] = {
                    "cmd": None,
                    "pkg": None,
                    "error": _(
                        "Empty command specified for menu item '{key}'.\n"
                        "Enter a valid command or reset the setting.\n\n{hint}"
                    ).format(key=k, hint=cfg_hint),
                }
            else:
                pkg_str = default_entry["pkg"] if cmd_str == default_cmd else _extract_binary(cmd_str)
                commands[k] = {"cmd": cmd_str, "pkg": pkg_str, "error": None}
        elif isinstance(v, dict):
            raw_cmd, raw_pkg = v.get("cmd"), v.get("pkg")
            if raw_cmd is not None and (not isinstance(raw_cmd, str) or not raw_cmd.strip()):
                commands[k] = {
                    "cmd": None,
                    "pkg": None,
                    "error": _(
                        "Invalid command ('cmd') for menu item '{key}'.\n"
                        "The value must be a non-empty string or null.\n\n{hint}"
                    ).format(key=k, hint=cfg_hint),
                }
                continue
            if raw_pkg is not None and (not isinstance(raw_pkg, str) or not raw_pkg.strip()):
                commands[k] = {
                    "cmd": raw_cmd,
                    "pkg": None,
                    "error": _(
                        "Invalid package name ('pkg') for menu item '{key}'.\n"
                        "Specify a valid APT package name or set 'pkg' to null.\n\n{hint}"
                    ).format(key=k, hint=cfg_hint),
                }
                continue

            cmd_str = raw_cmd.strip() if isinstance(raw_cmd, str) else None
            if "pkg" in v and raw_pkg is not None:
                pkg_str = raw_pkg.strip()
            else:
                pkg_str = default_entry["pkg"] if cmd_str == default_cmd else _extract_binary(cmd_str)

            commands[k] = {"cmd": cmd_str, "pkg": pkg_str, "error": None}
        else:
            commands[k] = {
                "cmd": None,
                "pkg": None,
                "error": _(
                    "Invalid configuration format for menu item '{key}'.\n"
                    "Expected a command string or an object {{\"cmd\": ..., \"pkg\": ...}}.\n\n{hint}"
                ).format(key=k, hint=cfg_hint),
            }

    if syntax_err_msg:
        if broken_key and broken_key in commands:
            commands[broken_key]["error"] = syntax_err_msg
        else:
            # Если ошибка в самом корне файла (например, забыта первая '{') и ключ не определить
            for k in commands:
                commands[k]["error"] = syntax_err_msg

    return commands


def resolve_action(cmd_key, commands_map=None, anchor=None):
    if commands_map is None:
        commands_map = load_winx_commands()

    default_cmd = DEFAULT_WINX_COMMANDS.get(cmd_key, {}).get("cmd")
    entry = commands_map.get(cmd_key, {"cmd": None, "pkg": None, "error": None})

    if entry.get("error"):
        return " [!]", lambda: _show_fallback_dialog(
            _("System Menu — Configuration Error"), entry["error"], default_cmd, anchor=anchor
        )

    cmd, pkg = entry.get("cmd"), entry.get("pkg")
    if not cmd:
        return " [X]", lambda: _show_message(
            Gtk.MessageType.INFO, _("System Menu"), _("No suitable application.\nUnder developing...")
        )

    if cmd in BUILTIN_HANDLERS:
        return "", BUILTIN_HANDLERS[cmd]
    if callable(cmd):
        return "", cmd

    binary = _extract_binary(cmd)
    if not binary:
        err = _(
            "Invalid command syntax for menu item '{key}'.\n"
            "Check the quotes and arguments in:\n{path}\n\n"
            "(or delete the file to restore defaults)\n\n"
        ).format(key=cmd_key, path=WINX_COMMANDS_FILE)
        return " [!]", lambda: _show_fallback_dialog(
            _("System Menu — Configuration Error"), err, default_cmd, anchor=anchor
        )

    if shutil.which(binary) is not None:
        return "", cmd

    effective_pkg = pkg or binary
    return " [!]", lambda k=cmd_key, b=binary, p=effective_pkg, d=default_cmd: _ask_and_install_with_fallback(
        k, b, p, d, anchor=anchor
    )


def execute_winx_key(cmd_key, anchor=None):
    commands_map = load_winx_commands()
    if cmd_key not in commands_map:
        return False
    _, action = resolve_action(cmd_key, commands_map=commands_map, anchor=anchor)
    if action is show_run_dialog:
        show_run_dialog(anchor)
    elif callable(action):
        action()
    else:
        run_command(action)
    return True

