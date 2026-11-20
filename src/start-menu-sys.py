import json
import os
import subprocess
import sys

from sys_actions import execute_winx_key
from sys_i18n import APP_VERSION, _
from sys_shortcuts import sync_plugin_shortcuts
from sys_winx_menu import show_winx_popup


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Libxfce4panel", "2.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Libxfce4panel

#from sys_i18n import APP_VERSION, _
#from sys_winx_menu import show_winx_popup


def setup_plugin(plugin):
    sync_plugin_shortcuts()
    button = Libxfce4panel.panel_create_toggle_button()

    tooltip_text = (
        "<tt>"
        f"<span alpha='35%'>Start Menu Ver. {APP_VERSION}</span>\n"
        f"{_('Left-click')}        - <b>{_('Applications Menu')}</b> [Win]\n"
        f"{_('Right-click')}       - <b>{_('System Menu')}</b>  [Win+X]\n"
        f"Shift+{_('Right-click')} - <b>{_('Panel Preferences')}</b>"
        "</tt>"
    )
    button.set_tooltip_markup(tooltip_text)

    icon_theme = Gtk.IconTheme.get_default()
    for name in ["xfce4-panel-menu", "start-here", "applications-system", "emblem-system"]:
        if icon_theme.has_icon(name):
            icon = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.LARGE_TOOLBAR)
            break
    else:
        icon = Gtk.Label(label="MENU")
    button.add(icon)

    def on_size_changed(plg, size):
        nrows = plg.get_nrows()
        row_size = size // nrows
        icon_size = max(16, row_size - 8)
        if isinstance(icon, Gtk.Image):
            icon.set_pixel_size(icon_size)
        plg.set_size_request(row_size, row_size)
        return True

    def get_button_anchor():
        win = button.get_window()
        if not win:
            return None
        _, win_x, win_y = win.get_origin()
        alloc = button.get_allocation()
        pos_name = plugin.get_screen_position().value_nick
        return (win_x + alloc.x, win_y + alloc.y, alloc.width, alloc.height, pos_name)

    def _wait_super_release_and_popup():
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        root_win = display.get_default_screen().get_root_window()
        _, _, _, state = root_win.get_device_position(pointer)

        if state & Gdk.ModifierType.MOD4_MASK:
            return True

        show_winx_popup(plugin, button, anchor=get_button_anchor())
        return False

    def trigger_start_menu():
        anchor = get_button_anchor()
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if anchor:
                param = GLib.Variant("(iiiis)", anchor)
                bus.call_sync(
                    "org.custom.xfce.startmenu",
                    "/org/custom/xfce/startmenu",
                    "org.freedesktop.Application",
                    "ActivateAction",
                    GLib.Variant("(sava{sv})", ("open-at", [param], {})),
                    None,
                    Gio.DBusCallFlags.NONE,
                    200,
                    None,
                )
            else:
                bus.call_sync(
                    "org.custom.xfce.startmenu",
                    "/org/custom/xfce/startmenu",
                    "org.freedesktop.Application",
                    "Activate",
                    GLib.Variant("(a{sv})", ({},)),
                    None,
                    Gio.DBusCallFlags.NONE,
                    200,
                    None,
                )
        except Exception:
            env = os.environ.copy()
            if anchor:
                env["START_MENU_ANCHOR"] = json.dumps(anchor)
            app_script = os.path.join(BASE_DIR, "start-menu-app.py")
            subprocess.Popen(["python3", app_script], env=env)

    def on_left_click(btn):
        if btn.get_active():
            trigger_start_menu()
            btn.set_active(False)

    def on_remote_event(plg, name, value):
        if name == "winx":
            GLib.timeout_add(20, _wait_super_release_and_popup)
            return True
        elif name == "start":
            trigger_start_menu()
            return True
        return execute_winx_key(name, get_button_anchor())

    def on_panel_button_press(btn, event):
        if event.button == 3 and not (event.state & Gdk.ModifierType.SHIFT_MASK):
            show_winx_popup(plugin, button, event, anchor=get_button_anchor())
            return True
        return False

    plugin.connect("remote-event", on_remote_event)
    plugin.connect("size-changed", on_size_changed)
    on_size_changed(plugin, plugin.get_size())

    button.connect("button-press-event", on_panel_button_press)
    button.connect("clicked", on_left_click)
    plugin.add(button)
    plugin.add_action_widget(button)
    button.show_all()
