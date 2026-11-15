import os
import gi
import json
import sys
import gettext
import locale
import subprocess
gi.require_version('Gtk', '3.0')
gi.require_version('Garcon', '1.0')
from pathlib import Path
from gi.repository import Gtk, Gdk, GLib, Garcon, Gio


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


class XfceStartMenu(Gtk.Window):
    def __init__(self):
        super().__init__(title="XFCE Start Menu")

        # path to config: ~/.config/xfce-start-menu/geometry.json
        config_dir = Path(GLib.get_user_config_dir()) / "xfce-start-menu"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = config_dir / "geometry.json"

        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.NONE)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_keep_above(True)
        self.set_resizable(True)

        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.ENTER_NOTIFY_MASK |
            Gdk.EventMask.LEAVE_NOTIFY_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK
        )

        self.is_resizing = False
        self.regrab_timer_id = None

        self.load_geometry()
        self.apply_border_css()

        self.connect("map-event", self.on_map_event)
        self.connect("button-press-event", self.on_button_press)
        self.connect("configure-event", self.on_configure_event)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("key-press-event", self.on_key_press)
        self.connect("leave-notify-event", self.on_leave_notify)
        self.connect("enter-notify-event", self.on_enter_notify)
        self.connect("delete-event", lambda w, e: (self.hide_menu(), True))

        Garcon.set_environment("XFCE")
        self.menu = Garcon.Menu.new_applications()

        self.seen_apps = set()
        self.all_unique_apps = []

        self.setup_ui()
        self.load_menu_data()

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        self.add(main_box)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Searching for apps...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        main_box.pack_start(self.search_entry, False, False, 0)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        main_box.pack_start(content_box, True, True, 0)

        self.cat_list = Gtk.ListBox()
        self.cat_list.connect("row-selected", self.on_category_selected)
        self.cat_scroll = Gtk.ScrolledWindow()
        self.cat_scroll.set_min_content_width(170)
        self.cat_scroll.add(self.cat_list)
        content_box.pack_start(self.cat_scroll, False, True, 0)
        
        self.app_list = Gtk.ListBox()
        self.app_list.set_activate_on_single_click(True)
        self.app_list.connect("row-activated", self.on_app_activated)
        app_scroll = Gtk.ScrolledWindow()
        app_scroll.add(self.app_list)
        content_box.pack_start(app_scroll, True, True, 0)

        # bottom line for actions
        self.footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.footer_box.set_margin_top(2)
        main_box.pack_end(self.footer_box, False, False, 0)

        # bottom line for sessionand version
        self.footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.footer_box.set_margin_top(2)
        main_box.pack_end(self.footer_box, False, False, 0)

        # list of session action
        session_actions = [
            ("system-lock-screen", _("Lock Screen"), ["xflock4"]),
            ("system-log-out",     _("Log Out"),     ["xfce4-session-logout", "--logout"]),
            None, 
            ("system-suspend",     _("Suspend"),     ["xfce4-session-logout", "--suspend"]),
            ("system-reboot",      _("Restart"),     ["xfce4-session-logout", "--reboot"]),
            ("system-shutdown",    _("Shut Down"),   ["xfce4-session-logout", "--halt"]),
        ]

        for item in session_actions:
            if item is None:
                sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
                sep.set_margin_top(4)
                sep.set_margin_bottom(4)
                sep.set_margin_start(2)
                sep.set_margin_end(2)
                self.footer_box.pack_start(sep, False, False, 0)
                continue

            icon_name, tooltip, cmd = item
            btn = Gtk.Button.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_tooltip_text(tooltip)
            btn.connect("clicked", self.on_session_action_clicked, cmd)
            self.footer_box.pack_start(btn, False, False, 0)

        ver_label = Gtk.Label()
        ver_label.set_markup(f"<small><span alpha='55%'>Ver. {APP_VERSION}</span></small>")
        ver_label.set_valign(Gtk.Align.CENTER)
        ver_label.set_margin_end(4)
        self.footer_box.pack_end(ver_label, False, False, 0)


    def log(self, msg):
        pass
        ### print(f"[DEBUG] {msg}", flush=True)

    def apply_border_css(self):
        css = b"""
        window {
            border: 1px solid @borders;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def load_geometry(self):
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                w = data.get("width", 520)
                h = data.get("height", 420)
                self.set_default_size(w, h)
                self.resize(w, h)
                return
            except Exception as e:
                print(f"Can't read geometry: {e}")

        self.set_default_size(520, 420)

    def save_geometry(self):
        try:
            width, height = self.get_size()
            data = {"width": width, "height": height}
            self.config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Can't save geometry: {e}")

    def reload_menu_data(self):
        # Запоминаем имя текущей выбранной категории, чтобы восстановить её после обновления
        selected_row = self.cat_list.get_selected_row()
        prev_cat_name = None
        if selected_row:
            lbl = selected_row.get_child()
            if isinstance(lbl, Gtk.Label):
                prev_cat_name = lbl.get_text()

        # Очищаем списки
        for child in self.cat_list.get_children():
            self.cat_list.remove(child)
        for child in self.app_list.get_children():
            self.app_list.remove(child)

        self.seen_apps.clear()
        self.all_unique_apps.clear()

        # Перечитываем .desktop файлы
        self.load_menu_data()
        self.cat_list.show_all()

        # Восстанавливаем выбор категории или берем первую
        target_row = self.cat_list.get_row_at_index(0)
        if prev_cat_name:
            for row in self.cat_list.get_children():
                lbl = row.get_child()
                if isinstance(lbl, Gtk.Label) and lbl.get_text() == prev_cat_name:
                    target_row = row
                    break
        if target_row:
            self.cat_list.select_row(target_row)

    def get_resize_edge(self, x, y):
        alloc = self.get_allocation()
        margin = 8

        on_free_h = (x >= alloc.width - margin) if self.expand_h == "east" else (x <= margin)
        on_free_v = (y <= margin) if self.expand_v == "north" else (y >= alloc.height - margin)

        if on_free_h and on_free_v:
            if self.expand_v == "north" and self.expand_h == "east":
                return Gdk.WindowEdge.NORTH_EAST
            elif self.expand_v == "north" and self.expand_h == "west":
                return Gdk.WindowEdge.NORTH_WEST
            elif self.expand_v == "south" and self.expand_h == "east":
                return Gdk.WindowEdge.SOUTH_EAST
            else:
                return Gdk.WindowEdge.SOUTH_WEST
        elif on_free_h:
            return Gdk.WindowEdge.EAST if self.expand_h == "east" else Gdk.WindowEdge.WEST
        elif on_free_v:
            return Gdk.WindowEdge.NORTH if self.expand_v == "north" else Gdk.WindowEdge.SOUTH
        return None

    def on_motion_notify(self, widget, event):
        window = self.get_window()
        if not window:
            return

        edge = self.get_resize_edge(event.x, event.y)
        if edge is None:
            window.set_cursor(None)
            return

        cursor_map = {
            Gdk.WindowEdge.NORTH_EAST:  Gdk.CursorType.TOP_RIGHT_CORNER,
            Gdk.WindowEdge.NORTH_WEST:  Gdk.CursorType.TOP_LEFT_CORNER,
            Gdk.WindowEdge.SOUTH_EAST:  Gdk.CursorType.BOTTOM_RIGHT_CORNER,
            Gdk.WindowEdge.SOUTH_WEST:  Gdk.CursorType.BOTTOM_LEFT_CORNER,
            Gdk.WindowEdge.NORTH:       Gdk.CursorType.TOP_SIDE,
            Gdk.WindowEdge.SOUTH:       Gdk.CursorType.BOTTOM_SIDE,
            Gdk.WindowEdge.EAST:        Gdk.CursorType.RIGHT_SIDE,
            Gdk.WindowEdge.WEST:        Gdk.CursorType.LEFT_SIDE,
        }
        cursor_type = cursor_map.get(edge)
        if cursor_type:
            window.set_cursor(
                Gdk.Cursor.new_for_display(self.get_display(), cursor_type)
            )

    def on_leave_notify(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL and event.detail != Gdk.NotifyType.INFERIOR:
            window = self.get_window()
            if window:
                window.set_cursor(None)
                default_cursor = Gdk.Cursor.new_for_display(
                    self.get_display(), Gdk.CursorType.LEFT_PTR
                )
                self.grab_seat(event, cursor=default_cursor)
        return False

    def on_enter_notify(self, widget, event):
        if event.mode == Gdk.CrossingMode.NORMAL and event.detail != Gdk.NotifyType.INFERIOR:
            self.grab_seat(event, cursor=None)
        return False

    def grab_seat(self, event=None, cursor=None):
        display = self.get_display()
        seat = display.get_default_seat()
        window = self.get_window()
        if window and seat and self.get_visible():
            status = seat.grab(
                window,
                Gdk.SeatCapabilities.POINTER | Gdk.SeatCapabilities.KEYBOARD,
                True,
                cursor,
                event,
                lambda s, w, d: w.show(),
                None
            )
            self.log(f"grab_seat -> status={status.value_nick}")
            return status == Gdk.GrabStatus.SUCCESS
        return False

    def on_map_event(self, widget, event):
        GLib.idle_add(lambda: (self.grab_seat(), False)[-1])
        return False

    def on_configure_event(self, widget, event):
        if self.is_resizing and self.regrab_timer_id is None:
            self.regrab_timer_id = GLib.timeout_add(50, self._regrab_after_resize)
        return False

    def _regrab_after_resize(self):
        if self.grab_seat():
            self.regrab_timer_id = None
            self.is_resizing = False
            w, h = self.get_size()
            self.set_default_size(w, h)
            self.save_geometry()
            return False
        return True

    def start_wm_drag(self, event, edge=None):
        self.is_resizing = True
        self.get_display().get_default_seat().ungrab()
        if edge is None:
            self.begin_move_drag(
                event.button, int(event.x_root), int(event.y_root), event.time
            )
        else:
            self.begin_resize_drag(
                edge, event.button, int(event.x_root), int(event.y_root), event.time
            )
        if self.regrab_timer_id is None:
            self.regrab_timer_id = GLib.timeout_add(50, self._regrab_after_resize)

    def get_free_corner_edge(self):
        if self.expand_v == "north" and self.expand_h == "east":
            return Gdk.WindowEdge.NORTH_EAST
        elif self.expand_v == "north" and self.expand_h == "west":
            return Gdk.WindowEdge.NORTH_WEST
        elif self.expand_v == "south" and self.expand_h == "east":
            return Gdk.WindowEdge.SOUTH_EAST
        return Gdk.WindowEdge.SOUTH_WEST

    def on_button_press(self, widget, event):
        alloc = self.get_allocation()
        # Click outside the window -> close it
        if (event.x < 0 or event.y < 0 or
            event.x > alloc.width or event.y > alloc.height):
            self.hide_menu()
            return True

        # Handling Alt + Left-click (moving) and Alt + Right-click (resizing)
        alt_pressed = bool(event.state & Gdk.ModifierType.MOD1_MASK)
        if alt_pressed:
            ### if event.button == 1:
            ###     self.start_wm_drag(event, edge=None)
            ###     return True
            ### elif event.button == 3:
            if event.button == 3:
                self.start_wm_drag(event, edge=self.get_free_corner_edge())
            return True

        # A standard left-click on the right or bottom edge -> resize
        if event.button == 1:
            edge = self.get_resize_edge(event.x, event.y)
            if edge is not None:
                self.start_wm_drag(event, edge=edge)
                return True

        return False

    def hide_menu(self):
        self.save_geometry()
        display = self.get_display()
        seat = display.get_default_seat()
        if seat:
            seat.ungrab()
        self.hide()

    def position_near_button(self, btn_x, btn_y, btn_w, btn_h, pos_name):
        win_w, win_h = self.get_default_size()
        if win_w <= 0 or win_h <= 0:
            win_w, win_h = self.get_size()
        pos = pos_name.lower()

        display = Gdk.Display.get_default()
        monitor = display.get_monitor_at_point(btn_x, btn_y)
        wa = monitor.get_workarea() if monitor else None

        # XfceScreenPosition (nw-h, n, ne-h, sw-h, s, se-h, w, nw-v, sw-v, e, ne-v, se-v)
        is_top = pos in ("n", "nw-h", "ne-h") or "top" in pos
        is_left = pos in ("w", "nw-v", "sw-v") or "left" in pos
        is_right = pos in ("e", "ne-v", "se-v") or "right" in pos

        # 1. Vertical connection (north / south)
        if is_top:
            # Panel on top -> anchor on top, resize only down (south)
            x = btn_x
            y = btn_y + btn_h
            self.expand_v = "south"
        elif is_left or is_right:
            x = (btn_x + btn_w) if is_left else (btn_x - win_w)
            if wa and ((btn_y + win_h > wa.y + wa.height) or (btn_y > wa.y + wa.height // 2)):
                y = btn_y + btn_h - win_h
                self.expand_v = "north"
            else:
                y = btn_y
                self.expand_v = "south"
        else:
            # Panel on bottom (s, sw-h, se-h) -> anchor on bottom, resize only up (north)
            x = btn_x
            y = btn_y - win_h
            self.expand_v = "north"

        # 2. Horiz commectyion (east / west)
        if is_right:
            self.expand_h = "west"
        elif is_left:
            self.expand_h = "east"
        else:
            # button on right side of screen -> resize only left (west)
            if wa and (btn_x + win_w > wa.x + wa.width) and (btn_x > wa.x + wa.width // 2):
                x = btn_x + btn_w - win_w
                self.expand_h = "west"
            else:
                self.expand_h = "east"

        # guard four out of screen
        if wa:
            x = max(wa.x, min(x, wa.x + wa.width - win_w))
            y = max(wa.y, min(y, wa.y + wa.height - win_h))

        self.move(int(x), int(y))

    def show_and_refresh(self, anchor=None):
        self.search_entry.set_text("")
        self.cat_scroll.show()
        self.reload_menu_data()
        self.load_geometry()

        if anchor is not None:
            self.position_near_button(*anchor)

        self.show_all()

        # retry position after show_all(), to ensure that XFWM4 do not put window in center of screen
        if anchor is not None:
            self.position_near_button(*anchor)
        else:
            self.load_geometry()

        self.present_with_time(Gdk.CURRENT_TIME)
        self.search_entry.grab_focus()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_menu()

    def load_menu_data(self):
        try:
            self.menu.load(None)
        except Exception as e:
            print(f"Can't load menu: {e}")
            return

        for submenu in self.menu.get_menus():
            if not submenu.get_visible():
                continue
            
            unique_items = []
            for item in submenu.get_items():
                if isinstance(item, Garcon.MenuItem) and item.get_visible():
                    app_id = item.get_desktop_id()
                    if app_id not in self.seen_apps:
                        self.seen_apps.add(app_id)
                        unique_items.append(item)
                        self.all_unique_apps.append(item)

            if unique_items:
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=submenu.get_name(), xalign=0)
                label.set_margin_top(6)
                label.set_margin_bottom(6)
                label.set_margin_start(8)
                row.add(label)
                row.apps = unique_items
                self.cat_list.add(row)

    def populate_app_list(self, apps):
        for child in self.app_list.get_children():
            self.app_list.remove(child)

        for app_item in apps:
            app_row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_top(5)
            box.set_margin_bottom(5)
            box.set_margin_start(8)

            icon_name = app_item.get_icon_name() or "application-x-executable"
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
            label = Gtk.Label(label=app_item.get_name(), xalign=0)

            box.pack_start(icon, False, False, 0)
            box.pack_start(label, True, True, 0)
            app_row.add(box)
            app_row.app_item = app_item

            gfile = app_item.get_file()
            full_path = gfile.get_path() if gfile else _("Path not found")
            desktop_id = app_item.get_desktop_id() or _("No ID")
            app_row.set_tooltip_text(f"ID:   {desktop_id}\n{_('File:')} {full_path}")

            self.app_list.add(app_row)

        self.app_list.show_all()

    def on_category_selected(self, listbox, row):
        if row is not None:
            self.populate_app_list(row.apps)

    def on_search_changed(self, entry):
        query = entry.get_text().strip().lower()
        if not query:
            self.cat_scroll.show()
            selected = self.cat_list.get_selected_row()
            if selected:
                self.populate_app_list(selected.apps)
            return

        self.cat_scroll.hide()
        filtered = [
            app for app in self.all_unique_apps
            if query in (app.get_name() or "").lower()
            or query in (app.get_comment() or "").lower()
        ]
        self.populate_app_list(filtered)

    def on_app_activated(self, listbox, row):
        if row and hasattr(row, 'app_item'):
            cmd = row.app_item.get_command()
            if cmd:
                # Убираем ключи %U, %F, %u, %f и лишние пробелы
                clean_cmd = cmd.split('%')[0].strip()
                try:
                    app_info = Gio.AppInfo.create_from_commandline(clean_cmd, None, 0)
                    app_info.launch(None, None)
                except Exception as e:
                    print(f"Run error '{clean_cmd}': {e}", flush=True)
                self.hide_menu()

    def on_session_action_clicked(self, button, cmd):
        self.hide_menu()
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            print(f"Failed to execute {cmd}: {e}")


class StartMenuApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.custom.xfce.startmenu")
        self.window = None
        self.hold()

        action = Gio.SimpleAction.new("open-at", GLib.VariantType.new("(iiiis)"))
        action.connect("activate", self.on_open_at)
        self.add_action(action)

    def on_open_at(self, action, parameter):
        anchor = parameter.unpack()
        if not self.window:
            self.window = XfceStartMenu()
            self.window.set_application(self)
        self.window.show_and_refresh(anchor=anchor)

    def do_activate(self):
     anchor = None
     raw_anchor = os.environ.pop("START_MENU_ANCHOR", None)
     if raw_anchor:
         try:
             anchor = tuple(json.loads(raw_anchor))
         except Exception:
             pass

     if not self.window:
         self.window = XfceStartMenu()
         self.window.set_application(self)
     self.window.show_and_refresh(anchor=anchor)

if __name__ == "__main__":
    app = StartMenuApp()
    app.run(sys.argv)
