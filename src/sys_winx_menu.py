import os
import json

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from sys_actions import resolve_action, run_command
from sys_cmd import show_run_dialog
from sys_i18n import _
from sys_shortcuts import DEFAULT_SHORTCUTS, ensure_plugin_shortcuts

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "xfce-start-menu")
WINX_KEYS_FILE = os.path.join(CONFIG_DIR, "winx_keys.json")

# Фиксированные клавиши по умолчанию (эталон Windows 11 Win+X)
DEFAULT_WINX_KEYS = {
    "installed_apps":   "F",
    "power":            "O",
    "event_viewer":     "V",
    "system":           "Y",
    "device_manager":   "M",
    "network":          "W",
    "disks":            "K",
    "computer_mgmt":    "G",
    "terminal":         "I",
    "terminal_admin":   "A",
    "task_manager":     "T",
    "settings":         "N",
    "file_explorer":    "E",
    "search":           "S",
    "run":              "R",
    "shutdown_menu":    "U",  # открытие подменю "Shutdown or sign out"
    "logout":           "I",  # внутри подменю выключения
    "suspend":          "S",
    "hibernate":        "H",
    "halt":             "U",
    "reboot":           "R",
    "desktop":          "D",
}


def load_winx_keys():
    keys = DEFAULT_WINX_KEYS.copy()
    try:
        if not os.path.exists(WINX_KEYS_FILE):
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(WINX_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_WINX_KEYS, f, indent=2, ensure_ascii=False)
            return keys

        with open(WINX_KEYS_FILE, "r", encoding="utf-8") as f:
            user_keys = json.load(f)
            if isinstance(user_keys, dict):
                keys.update({k: str(v).strip() for k, v in user_keys.items() if v})
    except Exception as e:
        print(f"[sys_winx_menu] Failed to load {WINX_KEYS_FILE}: {e}")
    return keys


def _parse_key_spec(spec):
    """Разбирает строку вида 'i' или 'A' в keyval в нижнем регистре."""
    if not spec:
        return None
    key_char = spec.strip().split("+")[-1].strip()
    if len(key_char) != 1:
        return None
    return Gdk.unicode_to_keyval(ord(key_char.lower()))


def _format_global_accel(cmd_key):
    """Возвращает строку глобального хоткея из DEFAULT_SHORTCUTS (если задан)."""
    entry = DEFAULT_SHORTCUTS.get(cmd_key)
    if entry and entry[0]:
        accel = entry[0]
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
    return None


def _format_tooltip_hint(cmd_key, winx_keys, parent_key=None):
    """Собирает итоговую подсказку для тултипа: 'Win+D  |  Win+X, D'."""
    parts = []

    global_accel = _format_global_accel(cmd_key)
    if global_accel:
        parts.append(global_accel)

    spec = winx_keys.get(cmd_key)
    if spec:
        key_upper = spec.strip().split("+")[-1].strip().upper()
        if parent_key and winx_keys.get(parent_key):
            parent_upper = winx_keys[parent_key].strip().split("+")[-1].strip().upper()
            parts.append(f"Win+X, {parent_upper} → {key_upper}")
        else:
            parts.append(f"Win+X, {key_upper}")

    return "  |  ".join(parts) if parts else None

def _attach_delayed_tooltip(widget, markup, delay_ms=2000):
    """Показывает нативный GTK tooltip строго через delay_ms + ~1000 мс (GtkTooltip)."""
    state = {"timer_id": None, "ready": False}
    widget.set_has_tooltip(True)

    def _on_timer():
        state["timer_id"] = None
        state["ready"] = True
        widget.trigger_tooltip_query()
        return False

    def _on_enter(w, event):
        if state["timer_id"] is None and not state["ready"]:
            state["timer_id"] = GLib.timeout_add(delay_ms, _on_timer)
        return False

    def _on_leave(w, event):
        if state["timer_id"] is not None:
            GLib.source_remove(state["timer_id"])
            state["timer_id"] = None
        state["ready"] = False
        return False

    def _on_query_tooltip(w, x, y, keyboard_mode, tooltip):
        if not state["ready"]:
            return False
        tooltip.set_markup(markup)
        return True

    widget.connect("enter-notify-event", _on_enter)
    widget.connect("leave-notify-event", _on_leave)
    widget.connect("destroy", lambda w: _on_leave(w, None))
    widget.connect("query-tooltip", _on_query_tooltip)


def _bind_menu_keypress(menu, keymap):
    """Перехватывает нажатия клавиш внутри открытого Gtk.Menu независимо от регистра и раскладки."""
    def _on_key_press(widget, event):
        ignored_mods = (
            Gdk.ModifierType.CONTROL_MASK
            | Gdk.ModifierType.MOD1_MASK
            | Gdk.ModifierType.SUPER_MASK
        )
        if event.state & ignored_mods:
            return False

        lower_keyval = Gdk.keyval_to_lower(event.keyval)
        target_item = keymap.get(lower_keyval)

        if target_item is None:
            display = Gdk.Display.get_default()
            gdk_keymap = Gdk.Keymap.get_for_display(display)
            ok, keyval, _, _, _ = gdk_keymap.translate_keyboard_state(
                event.hardware_keycode, Gdk.ModifierType(0), 0
            )
            if ok:
                target_item = keymap.get(Gdk.keyval_to_lower(keyval))

        if target_item is not None and target_item.get_sensitive():
            if target_item.get_submenu() is not None:
                menu.select_item(target_item)
                target_item.emit("activate")
            else:
                menu.popdown()
                target_item.activate()
            return True

        return False

    menu.connect("key-press-event", _on_key_press)


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
        (_("Shutdown or sign out"), ("shutdown_menu", [
            (_("Sign out"),         "logout"),
            (_("Sleep"),            "suspend"),
            (_("Hibernate"),        "hibernate"),
            (_("Shutdown"),         "halt"),
            (_("Restart"),          "reboot"),
        ])),
        (_("Desktop"),              "desktop"),
    ]
    # fmt: on


def build_menu_level(schema_list, winx_keys, anchor=None, parent_key=None):
    menu = Gtk.Menu()
    level_keymap = {}

    for entry in schema_list:
        if entry is None:
            menu.append(Gtk.SeparatorMenuItem())
            continue

        label_text, target = entry

        if isinstance(target, tuple):
            cmd_key, sub_schema = target
            item = Gtk.MenuItem(label=label_text)
            submenu = build_menu_level(
                sub_schema, winx_keys, anchor=anchor, parent_key=cmd_key
            )
            item.set_submenu(submenu)
        else:
            cmd_key = target
            if cmd_key == "run":
                item = Gtk.MenuItem(label=label_text)
                item.connect("activate", lambda w, a=anchor: show_run_dialog(a))
            else:
                suffix, action = resolve_action(cmd_key)
                item = Gtk.MenuItem(label=label_text + suffix)
                if callable(action):
                    item.connect("activate", lambda w, fn=action: fn())
                else:
                    item.connect("activate", lambda w, c=action: run_command(c))

        parsed = _parse_key_spec(winx_keys.get(cmd_key))
        if parsed:
            level_keymap[parsed] = item

        # Подключаем отложенный тултип (3000 мс (2000 + 1000 from GtkTooltip))
        hint = _format_tooltip_hint(cmd_key, winx_keys, parent_key=parent_key)
        if hint:
            _attach_delayed_tooltip(item, f"<tt><b>{hint}</b></tt>", delay_ms=2000)

        menu.append(item)

    _bind_menu_keypress(menu, level_keymap)
    return menu


def show_winx_popup(plugin, button, trigger_event=None, anchor=None):
    ensure_plugin_shortcuts(interactive=True)
    winx_keys = load_winx_keys()
    winx_popup = build_menu_level(get_winx_schema(), winx_keys, anchor=anchor)

    winx_popup.connect("deactivate", lambda menu: GLib.idle_add(menu.destroy))
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


