from gi.repository import Gtk, Gdk, GLib, Pango
from start_menu_app_constants import _
from start_menu_app_data import make_icon_widget


class PinnedSection(Gtk.Box):
    def __init__(self, config, repo, on_launch_cb, on_changed_cb, on_drag_end_cb=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.config = config
        self.repo = repo
        self.on_launch_cb = on_launch_cb
        self.on_changed_cb = on_changed_cb
        self._has_items = False

        # Состояние внутреннего перетаскивания
        self._drag_src_id = None
        self._drag_src_icon = None
        self._drag_src_btn = None
        self._drag_hover_btn = None
        self._drag_ghost_win = None
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_dragging = False

        # Заголовок-кнопка в едином стиле с All (стрелка + Pinned)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_top(2)
        header_box.set_margin_start(4)
        header_box.set_margin_end(4)

        self.section_btn = Gtk.Button()
        self.section_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.section_btn.get_style_context().add_class("section-header-btn")
        self.section_btn.connect("clicked", self._on_toggle_clicked)

        sec_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.section_arrow = Gtk.Image.new_from_icon_name(
            "pan-down-symbolic", Gtk.IconSize.MENU
        )
        self.section_label = Gtk.Label(label=_("Pinned"), xalign=0)
        self.section_label.get_style_context().add_class("section-title")

        sec_inner.pack_start(self.section_arrow, False, False, 0)
        sec_inner.pack_start(self.section_label, False, False, 0)
        self.section_btn.add(sec_inner)

        header_box.pack_start(self.section_btn, False, False, 0)
        self.pack_start(header_box, False, False, 0)

        # Заглушка для пустого списка закрепленных приложений
        self.empty_label = Gtk.Label(xalign=0)
        self.empty_label.set_margin_start(12)
        self.empty_label.set_margin_top(2)
        self.empty_label.set_margin_bottom(4)
        self.empty_label.set_markup(
            f"<small><span alpha='55%'>{_('No pinned apps yet (right-click an app to pin)')}</span></small>"
        )
        self.empty_label.set_no_show_all(True)
        self.pack_start(self.empty_label, False, False, 0)

        # Сетка закрепленных приложений (до 8 в ряд)
        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_valign(Gtk.Align.START)
        self.flow_box.set_max_children_per_line(8)
        self.flow_box.set_min_children_per_line(4)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_box.set_homogeneous(True)
        self.flow_box.set_row_spacing(6)
        self.flow_box.set_column_spacing(6)
        self.flow_box.set_no_show_all(True)
        self.pack_start(self.flow_box, False, False, 0)

    def refresh(self, is_searching=False, in_category=False):
        if is_searching or in_category:
            self.set_visible(False)
            return

        pinned_apps = self.repo.get_pinned_apps()
        self._has_items = bool(pinned_apps)
        self._rebuild_grid(pinned_apps)
        self.show_all()
        self.apply_expanded_state()

    def _rebuild_grid(self, pinned_apps):
        self._reset_drag_state()
        for child in self.flow_box.get_children():
            self.flow_box.remove(child)

        _, _, gap, vbox_sp, max_chars, max_cols = self.config.get_tile_spacing()
        self.flow_box.set_row_spacing(gap)
        self.flow_box.set_column_spacing(gap)
        self.flow_box.set_max_children_per_line(max_cols)

        for idx, app in enumerate(pinned_apps):
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.get_style_context().add_class("pinned-item")
            btn.set_tooltip_text(app["name"])
            btn.app_id = app["id"]

            btn.add_events(
                Gdk.EventMask.BUTTON_PRESS_MASK
                | Gdk.EventMask.BUTTON_RELEASE_MASK
                | Gdk.EventMask.POINTER_MOTION_MASK
            )

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

            btn.connect(
                "button-press-event",
                self._on_item_button_press,
                app,
                idx,
                len(pinned_apps),
            )
            btn.connect("motion-notify-event", self._on_item_motion)
            btn.connect("button-release-event", self._on_item_button_release, app)

            self.flow_box.add(btn)
            btn.show_all()

    # --- Внутреннее перетаскивание с визуальной иконкой у курсора ---
    def _create_ghost_icon(self, icon_name):
        ghost = Gtk.Window(type=Gtk.WindowType.POPUP)
        ghost.set_decorated(False)
        ghost.set_accept_focus(False)
        ghost.set_skip_taskbar_hint(True)
        ghost.set_keep_above(True)
        ghost.set_app_paintable(True)

        screen = ghost.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            ghost.set_visual(visual)

        img = make_icon_widget(icon_name, self.config.get_icon_pixel_size() + 2)
        ghost.add(img)
        ghost.show_all()
        ghost.set_opacity(0.85)
        return ghost

    def _on_item_button_press(self, btn, event, app, idx, total):
        if event.button == 1:
            self._drag_src_id = app["id"]
            self._drag_src_icon = app["icon_name"]
            self._drag_src_btn = btn
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self._is_dragging = False
            return False

        if event.button == 3:
            self._show_context_menu(event, app, idx, total)
            return True

        return False

    def _on_item_motion(self, btn, event):
        if self._drag_src_id is None:
            return False

        if not self._is_dragging:
            dx = abs(event.x_root - self._drag_start_x)
            dy = abs(event.y_root - self._drag_start_y)
            if dx < 6 and dy < 6:
                return False

            self._is_dragging = True
            if self._drag_src_btn:
                self._drag_src_btn.set_opacity(0.35)
            self._drag_ghost_win = self._create_ghost_icon(self._drag_src_icon)

        # Двигаем иконку-призрак вслед за курсором (со смещением, чтобы не перекрывать клик)
        if self._drag_ghost_win:
            self._drag_ghost_win.move(int(event.x_root) + 12, int(event.y_root) + 12)

        # Подсвечиваем целевую плитку под курсором
        target_btn = self._find_button_at_root(event.x_root, event.y_root)
        if target_btn is not self._drag_hover_btn:
            if self._drag_hover_btn:
                self._drag_hover_btn.get_style_context().remove_class(
                    "pinned-drop-target"
                )
            self._drag_hover_btn = target_btn
            if target_btn and target_btn is not self._drag_src_btn:
                target_btn.get_style_context().add_class("pinned-drop-target")

        return True

    def _on_item_button_release(self, btn, event, app):
        if event.button != 1:
            return False

        was_dragging = self._is_dragging
        src_id = self._drag_src_id
        target_btn = self._find_button_at_root(event.x_root, event.y_root)
        dst_id = getattr(target_btn, "app_id", None) if target_btn else None

        self._reset_drag_state()

        if was_dragging:
            if src_id and dst_id and src_id != dst_id:
                self.config.reorder_pinned(src_id, dst_id)
                GLib.idle_add(lambda: (self.on_changed_cb(save_geom=False), False)[ -1 ])
            return True

        self.on_launch_cb(app)
        return True

    def _find_button_at_root(self, x_root, y_root):
        flow_win = self.flow_box.get_window()
        if not flow_win:
            return None
        _, fx, fy = flow_win.get_origin()
        rel_x = x_root - fx
        rel_y = y_root - fy
        child = self.flow_box.get_child_at_pos(int(rel_x), int(rel_y))
        return child.get_child() if child else None

    def _reset_drag_state(self):
        if self._drag_ghost_win:
            self._drag_ghost_win.destroy()
            self._drag_ghost_win = None
        if self._drag_src_btn:
            self._drag_src_btn.set_opacity(1.0)
        if self._drag_hover_btn:
            self._drag_hover_btn.get_style_context().remove_class("pinned-drop-target")
        self._drag_src_id = None
        self._drag_src_icon = None
        self._drag_src_btn = None
        self._drag_hover_btn = None
        self._is_dragging = False

    # --- Сворачивание и контекстное меню ---

    def apply_expanded_state(self):
        expanded = self.config.pinned_expanded
        icon = "pan-down-symbolic" if expanded else "pan-end-symbolic"
        self.section_arrow.set_from_icon_name(icon, Gtk.IconSize.MENU)

        self.flow_box.set_visible(expanded and self._has_items)
        self.empty_label.set_visible(expanded and not self._has_items)

    def _on_toggle_clicked(self, button):
        self.config.pinned_expanded = not self.config.pinned_expanded
        self.apply_expanded_state()
        self.on_changed_cb(save_geom=True)

    def _show_context_menu(self, event, app, idx, total):
        menu = Gtk.Menu()

        unpin_item = Gtk.MenuItem(label=_("Unpin from top"))
        unpin_item.connect("activate", lambda w: self._unpin(app["id"]))
        menu.append(unpin_item)

        if total > 1:
            menu.append(Gtk.SeparatorMenuItem())
            if idx > 0:
                left_item = Gtk.MenuItem(label=_("Move left"))
                left_item.connect("activate", lambda w: self._move(app["id"], -1))
                menu.append(left_item)
            if idx < total - 1:
                right_item = Gtk.MenuItem(label=_("Move right"))
                right_item.connect("activate", lambda w: self._move(app["id"], 1))
                menu.append(right_item)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _unpin(self, app_id):
        self.config.toggle_pin(app_id)
        self.on_changed_cb(save_geom=False)

    def _move(self, app_id, delta):
        self.config.move_pinned(app_id, delta)
        self.on_changed_cb(save_geom=False)
