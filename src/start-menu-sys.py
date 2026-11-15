import os
import gi
import json
import subprocess
import gettext
import locale
gi.require_version('Gtk', '3.0')
gi.require_version('Libxfce4panel', '2.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Libxfce4panel


APP_DOMAIN = "xfce-start-menu"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_LOCALE_DIR = os.path.join(BASE_DIR, "locale")
SYS_LOCALE_DIR = "/usr/share/locale"
if os.path.isdir(LOCAL_LOCALE_DIR):
    LOCALE_DIR = LOCAL_LOCALE_DIR
else:
    LOCALE_DIR = SYS_LOCALE_DIR
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

def setup_plugin(plugin):
    winx_items = [
        (_("Terminal"),             "xfce4-terminal"),
        (_("Task Manager"),         "xfce4-taskmanager"),
        (_("System Settings"),      "xfce4-settings-manager"),
        (_("Display Settings"),     "xfce4-display-settings"),
        (_("Network Connections"),  "nm-connection-editor"),
        (_("Power Manager"),        "xfce4-power-manager-settings"),
    ]

    button = Libxfce4panel.panel_create_toggle_button()

    tooltip_text = (
        "<tt>"
        f"<span alpha='65%'>Start Menu Ver. {APP_VERSION}</span>\n"
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

    # 3. Обработка вызова Win+X по горячей клавише (remote-event)
    def _show_winx_popup(trigger_event=None):
        winx_popup = Gtk.Menu()
        for label_text, cmd in winx_items:
            item = Gtk.MenuItem(label=label_text)
            item.connect("activate", lambda w, c=cmd: subprocess.Popen(c.split()))
            winx_popup.append(item)

        winx_popup.connect("deactivate", lambda m: GLib.idle_add(m.destroy))
        winx_popup.show_all()
        plugin.register_menu(winx_popup)

        if trigger_event is None:
            trigger_event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
            trigger_event.window = button.get_window()
            trigger_event.time = Gtk.get_current_event_time()
            seat = Gdk.Display.get_default().get_default_seat()
            if seat:
                trigger_event.set_device(seat.get_pointer())

        # Выбираем правильную привязку к грани кнопки с учетом стороны панели
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

    def _wait_super_release_and_popup():
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        root_win = display.get_default_screen().get_root_window()
        _, _, _, state = root_win.get_device_position(pointer)
        
        if state & Gdk.ModifierType.MOD4_MASK:
            return True
            
        _show_winx_popup()
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
                    None
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
                    None
                )
        except Exception:
            env = os.environ.copy()
            if anchor:
                env["START_MENU_ANCHOR"] = json.dumps(anchor)
            app_script = os.path.join(BASE_DIR, "start-menu-app.py")
            subprocess.Popen(
                ["python3", app_script],
                env=env
            )

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
        return False

    def get_button_anchor():
        win = button.get_window()
        if not win:
            return None
        # Получаем экранные координаты окна плагина и смещение самой кнопки внутри него
        _, win_x, win_y = win.get_origin()
        alloc = button.get_allocation()
        btn_x = win_x + alloc.x
        btn_y = win_y + alloc.y
        btn_w = alloc.width
        btn_h = alloc.height

        # Определяем, у какого края экрана стоит панель
        screen_pos = plugin.get_screen_position()
        pos_name = screen_pos.value_nick  # например: 'bottom', 'top', 'left', 'right', 'floating-h'
        return (btn_x, btn_y, btn_w, btn_h, pos_name)


    # 5. Сборка виджета и контекстного меню ПКМ панели
    plugin.connect("remote-event", on_remote_event)
    plugin.connect("size-changed", on_size_changed)
    on_size_changed(plugin, plugin.get_size())

    def on_panel_button_press(btn, event):
        # Перехватываем обычный ПКМ (без Shift) на кнопке панели
        if event.button == 3 and not (event.state & Gdk.ModifierType.SHIFT_MASK):
            _show_winx_popup(event)
            return True  # Не даём панели открыть стандартное меню в точке курсора
        return False


    button.connect("button-press-event", on_panel_button_press)
    button.connect("clicked", on_left_click)
    plugin.add(button)
    plugin.add_action_widget(button)
    button.show_all()
