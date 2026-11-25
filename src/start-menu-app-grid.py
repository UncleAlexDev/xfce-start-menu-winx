from gi.repository import Gtk, GLib, Pango
from start_menu_app_constants import _
from start_menu_app_data import make_icon_widget


class LetterGridView(Gtk.Box):
    def __init__(self, config, on_launch_cb, on_context_menu_cb):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.config = config
        self.on_launch_cb = on_launch_cb
        self.on_context_menu_cb = on_context_menu_cb

    def populate(self, apps, use_letter_breaks=True):
        for child in self.get_children():
            self.remove(child)

        if not apps:
            return

        if not use_letter_breaks:
            flow = self._create_flow_box()
            for app in apps:
                flow.add(self._create_app_tile(app))
            self.pack_start(flow, False, False, 0)
            self.show_all()
            return

        # Группировка по первой букве — идентично List 1
        groups = []
        current_letter = None
        current_apps = []

        for app in apps:
            first_char = app["name"][:1].upper() if app["name"] else "#"
            if not first_char.isalpha():
                first_char = "#"

            if first_char != current_letter:
                if current_apps:
                    groups.append((current_letter, current_apps))
                current_letter = first_char
                current_apps = [app]
            else:
                current_apps.append(app)

        if current_apps:
            groups.append((current_letter, current_apps))

        # Отрисовка каждой буквенной секции
        for grp_idx, (letter, grp_apps) in enumerate(groups):
            letter_lbl = Gtk.Label(xalign=0)
            letter_lbl.set_margin_start(6)
            letter_lbl.set_margin_top(10 if grp_idx > 0 else 2)
            letter_lbl.set_margin_bottom(2)
            letter_lbl.set_markup(
                f"<b><span size='large'>{GLib.markup_escape_text(letter)}</span></b>"
            )
            self.pack_start(letter_lbl, False, False, 0)

            flow = self._create_flow_box()
            for app in grp_apps:
                flow.add(self._create_app_tile(app))
            self.pack_start(flow, False, False, 0)

        self.show_all()

    def _create_flow_box(self):
        pv, ph, gap, vbox_sp, max_chars, max_cols = self.config.get_tile_spacing()
        flow = Gtk.FlowBox()
        flow.set_valign(Gtk.Align.START)
        flow.set_max_children_per_line(max_cols)
        flow.set_min_children_per_line(4)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_row_spacing(gap)
        flow.set_column_spacing(gap)
        return flow

    def _create_app_tile(self, app):
        pv, ph, gap, vbox_sp, max_chars, max_cols = self.config.get_tile_spacing()

        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.get_style_context().add_class("grid-item")

        tooltip = (
            f"ID: {app['id']}\n"
            f"{_('File:')} {app['filename']}\n"
            f"{_('Categories:')} {app['raw_hint']}"
        )
        btn.set_tooltip_text(tooltip)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=vbox_sp)
        vbox.set_halign(Gtk.Align.CENTER)

        icon_px = self.config.get_icon_pixel_size()
        icon_w = make_icon_widget(app["icon_name"], icon_px)
        icon_w.set_halign(Gtk.Align.CENTER)

        lbl = Gtk.Label(label=app["name"])
        lbl.set_max_width_chars(max_chars)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        lbl.set_justify(Gtk.Justification.CENTER)

        vbox.pack_start(icon_w, False, False, 0)
        vbox.pack_start(lbl, False, False, 0)
        btn.add(vbox)

        btn.connect("clicked", lambda w, a=app: self.on_launch_cb(a))
        btn.connect("button-press-event", self._on_tile_button_press, app)
        return btn

    def _on_tile_button_press(self, btn, event, app):
        if event.button == 3:
            self.on_context_menu_cb(app, event)
            return True
        return False
