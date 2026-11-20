import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from sys_actions import resolve_action, run_command
from sys_cmd import show_run_dialog
from sys_i18n import _
from sys_shortcuts import DEFAULT_SHORTCUTS


def _format_accel_hint(cmd_key):
    """Возвращает строку хоткея из DEFAULT_SHORTCUTS или MENU_MNEMONICS (всегда в верхнем регистре)."""
    entry = DEFAULT_SHORTCUTS.get(cmd_key)
    if entry and entry[ 0 ]:
        accel = entry[ 0 ]
        formatted = (
            accel.replace("<Super>", "Win+")
            .replace("<Primary>", "Ctrl+")
            .replace("<Control>", "Ctrl+")
            .replace("<Alt>", "Alt+")
            .replace("<Shift>", "Shift+")
            .replace("Super_L", "Win")
        )
        if "+" in formatted:
            prefix, key = formatted.rsplit("+", 1)
            if len(key) == 1:
                formatted = f"{prefix}+{key.upper()}"
        return formatted

    mnemonic = MENU_MNEMONICS.get(cmd_key)
    if mnemonic:
        return f"Win+X, {mnemonic[ 0 ].upper()}"

    return None

def get_winx_schema():
    # fmt: off
    return [
        (_("Installed apps"),       "installed_apps"),
        (_("Power Options"),        "power"),
        (_("Event Viewer"),         "event_viewer"),
        (_("System"),               "system"),
        (_("Device Manager"),       "device_manager"),
        (_("Network Connections"),  "network"),
        (_("Disk Management"),      "disks"),
        (_("Computer Management"),  "computer_mgmt"),
        None,
        (_("Term_inal"),            "terminal"),
        (_("Terminal (_Admin)"),    "terminal_admin"),
        None,
        (_("Task Manager"),         "task_manager"),
        (_("Settings"),             "settings"),
        (_("File Explorer"),        "file_explorer"),
        (_("Search"),               "search"),
        (_("_Run"),                 "run"),
        None,
        (_("Shut down or sign out"), [
            (_("Sign out"),         "logout"),
            (_("Sleep"),            "suspend"),
            (_("Hibernate"),        "hibernate"),
            (_("Shut down"),        "halt"),
            (_("Restart"),          "reboot"),
        ]),
        (_("Desktop"),              "desktop"),
    ]
    # fmt: on


def build_menu_level(schema_list, anchor=None):
    menu = Gtk.Menu()
    for entry in schema_list:
        if entry is None:
            menu.append(Gtk.SeparatorMenuItem())
            continue

        label_text, target = entry
        if isinstance(target, list):
            item = Gtk.MenuItem(label=label_text, use_underline=True)
            item.set_submenu(build_menu_level(target, anchor=anchor))
        elif target == "run":
            item = Gtk.MenuItem(label=label_text, use_underline=True)
            item.connect("activate", lambda w, a=anchor: show_run_dialog(a))
        else:
            suffix, action = resolve_action(target)
            item = Gtk.MenuItem(label=label_text + suffix, use_underline=True)
            if callable(action):
                item.connect("activate", lambda w, fn=action: fn())
            else:
                item.connect("activate", lambda w, c=action: run_command(c))

        if isinstance(target, str):
            hint = _format_accel_hint(target)
            if hint:
                item.set_tooltip_markup(f"<tt><b>{hint}</b></tt>")

        menu.append(item)
    return menu


import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from sys_actions import execute_winx_key, resolve_action, run_command
from sys_cmd import show_run_dialog
from sys_i18n import _
from sys_shortcuts import DEFAULT_SHORTCUTS, MENU_MNEMONICS


def _format_accel_hint(cmd_key):
    """Возвращает строку хоткея из DEFAULT_SHORTCUTS или MENU_MNEMONICS (всегда в верхнем регистре)."""
    entry = DEFAULT_SHORTCUTS.get(cmd_key)
    if entry and entry[ 0 ]:
        accel = entry[ 0 ]
        formatted = (
            accel.replace("<Super>", "Win+")
            .replace("<Primary>", "Ctrl+")
            .replace("<Control>", "Ctrl+")
            .replace("<Alt>", "Alt+")
            .replace("<Shift>", "Shift+")
            .replace("Super_L", "Win")
        )
        if "+" in formatted:
            prefix, key = formatted.rsplit("+", 1)
            if len(key) == 1:
                formatted = f"{prefix}+{key.upper()}"
        return formatted

    mnemonic = MENU_MNEMONICS.get(cmd_key)
    if mnemonic and mnemonic[ 0 ]:
        return f"Win+X, {mnemonic[ 0 ].upper()}"

    return None


def get_winx_schema():
    # fmt: off
    return [
        (_("Installed apps"),       "installed_apps"),
        (_("Power Options"),        "power"),
        (_("Event Viewer"),         "event_viewer"),
        (_("System"),               "system"),
        (_("Device Manager"),       "device_manager"),
        (_("Network Connections"),  "network"),
        (_("Disk Management"),      "disks"),
        (_("Computer Management"),  "computer_mgmt"),
        None,
        (_("Terminal"),             "terminal"),
        (_("Terminal (Admin)"),     "terminal_admin"),
        None,
        (_("Task Manager"),         "task_manager"),
        (_("Settings"),             "settings"),
        (_("File Explorer"),        "file_explorer"),
        (_("Search"),               "search"),
        (_("Run"),                  "run"),
        None,
        (_("Shut down or sign out"), [
            (_("Sign out"),         "logout"),
            (_("Sleep"),            "suspend"),
            (_("Hibernate"),        "hibernate"),
            (_("Shut down"),        "halt"),
            (_("Restart"),          "reboot"),
        ]),
        (_("Desktop"),              "desktop"),
    ]
    # fmt: on


def build_menu_level(schema_list, anchor=None):
    menu = Gtk.Menu()
    for entry in schema_list:
        if entry is None:
            menu.append(Gtk.SeparatorMenuItem())
            continue

        label_text, target = entry
        if isinstance(target, list):
            item = Gtk.MenuItem(label=label_text)
            item.set_submenu(build_menu_level(target, anchor=anchor))
        elif target == "run":
            item = Gtk.MenuItem(label=label_text)
            item.connect("activate", lambda w, a=anchor: show_run_dialog(a))
        else:
            suffix, action = resolve_action(target)
            item = Gtk.MenuItem(label=label_text + suffix)
            if callable(action):
                item.connect("activate", lambda w, fn=action: fn())
            else:
                item.connect("activate", lambda w, c=action: run_command(c))

        if isinstance(target, str):
            hint = _format_accel_hint(target)
            if hint:
                item.set_tooltip_markup(f"<tt>{_('Shortcut')}: <b>{hint}</b></tt>")

        menu.append(item)
    return menu


def show_winx_popup(plugin, button, trigger_event=None, anchor=None):
    settings = Gtk.Settings.get_default()
    old_timeout = settings.get_property("gtk-tooltip-timeout")
    settings.set_property("gtk-tooltip-timeout", 5000)

    winx_popup = build_menu_level(get_winx_schema(), anchor=anchor)

    def _on_deactivate(menu):
        settings.set_property("gtk-tooltip-timeout", old_timeout)
        GLib.idle_add(menu.destroy)

    def _on_menu_key_press(menu, event):
        for cmd_key, (letter, hw_code) in MENU_MNEMONICS.items():
            low = letter.lower()
            high = letter.upper()
            if event.hardware_keycode == hw_code or event.keyval in (
                Gdk.unicode_to_keyval(ord(low)),
                Gdk.unicode_to_keyval(ord(high)),
            ):
                menu.popdown()
                execute_winx_key(cmd_key)
                return True
        return False

    winx_popup.connect("deactivate", _on_deactivate)
    winx_popup.connect("key-press-event", _on_menu_key_press)
    winx_popup.show_all()
    plugin.register_menu(winx_popup)

    if trigger_event is None:
        trigger_event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        trigger_event.window = button.get_window()
        trigger_event.time = Gtk.get_current_event_time()
        seat = Gdk.Display.get_default().get_default_seat()
        if seat:
            trigger_event.set_device(seat.get_pointer())

    pos = plugin.get_screen_position().value_nick.lower()
    if pos in ("n", "nw-h", "ne-h"):
        widget_anchor, menu_anchor = Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST
    elif pos in ("w", "nw-v", "sw-v"):
        widget_anchor, menu_anchor = Gdk.Gravity.NORTH_EAST, Gdk.Gravity.NORTH_WEST
    elif pos in ("e", "ne-v", "se-v"):
        widget_anchor, menu_anchor = Gdk.Gravity.NORTH_WEST, Gdk.Gravity.NORTH_EAST
    else:
        widget_anchor, menu_anchor = Gdk.Gravity.NORTH_WEST, Gdk.Gravity.SOUTH_WEST

    winx_popup.popup_at_widget(button, widget_anchor, menu_anchor, trigger_event)
    return False


