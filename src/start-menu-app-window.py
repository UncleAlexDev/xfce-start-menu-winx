
from gi.repository import Gtk, Gdk, GLib, Pango
from start_menu_app_constants import APP_VERSION, CATEGORY_NAMES, APP_CSS, _
from start_menu_app_config import MenuConfigManager
from start_menu_app_data import AppRepository, make_icon_widget
from start_menu_app_pinned import PinnedSection
from start_menu_app_grid import LetterGridView

from start_menu_app_constants import (
    APP_VERSION,
    CATEGORY_NAMES,
    APP_CSS,
    ICON_SIZE_PRESETS,
    TILE_PADDING_PRESETS,
    LABEL_SIZE_PRESETS,
    _,
)

class XfceStartMenu(Gtk.Window):
    def __init__(self):
        super().__init__(title="XFCE Start Menu")

        self.config = MenuConfigManager()
        self.repo = AppRepository(self.config)

        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.NONE)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
        self.set_keep_above(True)
        self.set_resizable(True)

        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.ENTER_NOTIFY_MASK
            | Gdk.EventMask.LEAVE_NOTIFY_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
        )

        self.is_resizing = False
        self.regrab_timer_id = None
        self.expand_h = "east"
        self.expand_v = "north"

        self.active_category_filter = None
        self._current_rendered_apps = []

        self.set_default_size(self.config.width, self.config.height)
        self.resize(self.config.width, self.config.height)
        self.apply_css()

        self.connect("map-event", self.on_map_event)
        self.connect("button-press-event", self.on_button_press)
        self.connect("configure-event", self.on_configure_event)
        self.connect("motion-notify-event", self.on_motion_notify)
        self.connect("key-press-event", self.on_key_press)
        self.connect("leave-notify-event", self.on_leave_notify)
        self.connect("enter-notify-event", self.on_enter_notify)
        self.connect("delete-event", lambda w, e: (self.hide_menu(), True))

        self.setup_ui()
        self.reload_menu_data()

    def apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(APP_CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.dynamic_css_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self.dynamic_css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )
        self.apply_dynamic_tile_css()

    def apply_dynamic_tile_css(self):
        pv, ph, _gap, _vbox_sp, _max_chars, _max_cols = self.config.get_tile_spacing()
        font_em = self.config.get_label_font_css()
        css = f"""
        button.pinned-item, button.grid-item {{
            padding: {pv}px {ph}px;
        }}
        button.pinned-item label, button.grid-item label {{
            font-size: {font_em};
        }}
        """.encode("utf-8")
        self.dynamic_css_provider.load_from_data(css)

    def build_settings_popover(self):
        popover = Gtk.Popover()
        popover.set_constrain_to(Gtk.PopoverConstraint.NONE)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_size_request(180, -1)

        # Секция 1: Размер иконок
        lbl_size = Gtk.Label(xalign=0)
        lbl_size.set_markup(f"<b><small>{_('Icon size')}</small></b>")
        box.pack_start(lbl_size, False, False, 2)

        self.icon_size_checks = {}
        for preset_id, title, _px in ICON_SIZE_PRESETS:
            btn = self._make_popover_check_item(
                title,
                preset_id == self.config.icon_size_preset,
                self._on_icon_size_selected,
                preset_id,
                self.icon_size_checks,
            )
            box.pack_start(btn, False, False, 0)

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        # Секция 2: Отступы внутри плиток
        lbl_pad = Gtk.Label(xalign=0)
        lbl_pad.set_markup(f"<b><small>{_('Item spacing')}</small></b>")
        box.pack_start(lbl_pad, False, False, 2)

        self.tile_pad_checks = {}
        for preset_id, title, _pad in TILE_PADDING_PRESETS:
            btn = self._make_popover_check_item(
                title,
                preset_id == self.config.tile_padding_preset,
                self._on_tile_padding_selected,
                preset_id,
                self.tile_pad_checks,
            )
            box.pack_start(btn, False, False, 0)

        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        # Секция 3: labels size
        lbl_font = Gtk.Label(xalign=0)
        lbl_font.set_markup(f"<b><small>{_('Label size')}</small></b>")
        box.pack_start(lbl_font, False, False, 2)

        self.label_size_checks = {}
        for preset_id, title, _em in LABEL_SIZE_PRESETS:
            btn = self._make_popover_check_item(
                title,
                preset_id == self.config.label_size_preset,
                self._on_label_size_selected,
                preset_id,
                self.label_size_checks,
            )
            box.pack_start(btn, False, False, 0)

        box.show_all()
        popover.add(box)
        self.settings_btn.set_popover(popover)

    def _make_popover_check_item(self, title, is_active, callback, preset_id, checks_dict):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        img = Gtk.Image.new_from_icon_name("object-select-symbolic", Gtk.IconSize.MENU)
        img.set_opacity(1.0 if is_active else 0.0)
        lbl = Gtk.Label(label=title, xalign=0)
        row.pack_start(img, False, False, 0)
        row.pack_start(lbl, True, True, 0)
        btn.add(row)
        btn.connect("clicked", callback, preset_id)
        checks_dict[preset_id] = img
        return btn

    def _on_icon_size_selected(self, button, preset_id):
        self.config.icon_size_preset = preset_id
        for pid, img in self.icon_size_checks.items():
            img.set_opacity(1.0 if pid == preset_id else 0.0)
        self.refresh_current_view()
        self.save_geometry()

    def _on_tile_padding_selected(self, button, preset_id):
        self.config.tile_padding_preset = preset_id
        for pid, img in self.tile_pad_checks.items():
            img.set_opacity(1.0 if pid == preset_id else 0.0)
        self.apply_dynamic_tile_css()
        self.refresh_current_view()
        self.save_geometry()

    def _on_label_size_selected(self, button, preset_id):
        self.config.label_size_preset = preset_id
        for pid, img in self.label_size_checks.items():
            img.set_opacity(1.0 if pid == preset_id else 0.0)
        self.apply_dynamic_tile_css()
        self.save_geometry()

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(14)
        main_box.set_margin_end(14)
        self.add(main_box)

        # 1. Поиск + кнопка настроек (шестеренка)
        search_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Search for apps..."))
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_row.pack_start(self.search_entry, True, True, 0)

        self.settings_btn = Gtk.MenuButton()
        self.settings_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.settings_btn.set_tooltip_text(_("Appearance settings"))
        gear_icon = Gtk.Image.new_from_icon_name(
            "emblem-system-symbolic", Gtk.IconSize.MENU
        )
        self.settings_btn.add(gear_icon)
        self.build_settings_popover()
        search_row.pack_end(self.settings_btn, False, False, 0)

        main_box.pack_start(search_row, False, False, 0)

        # 2. Общая прокручиваемая область (Pinned + All)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.pack_start(self.scroll, True, True, 0)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.scroll.add(self.content_box)

        # 2a. Секция Pinned
        self.pinned_section = PinnedSection(
            config=self.config,
            repo=self.repo,
            on_launch_cb=self.launch_app,
            on_changed_cb=self._on_pinned_changed,
            on_drag_end_cb=lambda: GLib.idle_add(lambda: (self.grab_seat(), False)[ -1 ]),
        )
        self.content_box.pack_start(self.pinned_section, False, False, 0)

        # 2b. Заголовок секции All (кликабельный для сворачивания)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header_box.set_margin_top(2)
        header_box.set_margin_start(4)
        header_box.set_margin_end(4)

        self.back_btn = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.MENU
        )
        self.back_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.back_btn.set_tooltip_text(_("Back to categories"))
        self.back_btn.connect("clicked", self.on_back_to_categories)
        self.back_btn.set_no_show_all(True)
        header_box.pack_start(self.back_btn, False, False, 0)

        self.section_btn = Gtk.Button()
        self.section_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.section_btn.get_style_context().add_class("section-header-btn")
        self.section_btn.connect("clicked", self.on_all_header_clicked)

        sec_inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.section_arrow = Gtk.Image.new_from_icon_name(
            "pan-down-symbolic", Gtk.IconSize.MENU
        )
        self.section_label = Gtk.Label(label=_("All"), xalign=0)
        self.section_label.get_style_context().add_class("section-title")

        sec_inner.pack_start(self.section_arrow, False, False, 0)
        sec_inner.pack_start(self.section_label, False, False, 0)
        self.section_btn.add(sec_inner)
        header_box.pack_start(self.section_btn, False, False, 0)

        self.view_btn = Gtk.MenuButton()
        self.view_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.view_btn.get_style_context().add_class("view-btn")
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.view_btn_label = Gtk.Label()
        arrow = Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.MENU)
        btn_box.pack_start(self.view_btn_label, False, False, 0)
        btn_box.pack_start(arrow, False, False, 0)
        self.view_btn.add(btn_box)

        self.build_view_popover()
        header_box.pack_end(self.view_btn, False, False, 0)
        self.content_box.pack_start(header_box, False, False, 0)

        titles = {
            "category": _("View: Category"),
            "list1": _("View: List 1"),
            "list2": _("View: List 2"),
            "grid": _("View: Grid"),
        }
        self.view_btn_label.set_text(
            titles.get(self.config.view_mode, _("View: List 1"))
        )

        # 2c. Контент секции All (Stack: List / Category)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        self.content_box.pack_start(self.stack, True, True, 0)

        # Tab 1: LIST
        self.list_store = Gtk.ListStore(str, str, str, str, int, bool)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_headers_visible(True)
        self.tree_view.set_activate_on_single_click(True)
        self.tree_view.set_tooltip_column(3)
        self.tree_view.connect("row-activated", self.on_tree_row_activated)
        self.tree_view.connect("button-press-event", self.on_tree_button_press)

        selection = self.tree_view.get_selection()
        selection.set_select_function(
            lambda sel, model, path, pcs, data: not model.get_value(
                model.get_iter(path), 5
            ),
            None,
        )

        col_app = Gtk.TreeViewColumn(_("Application"))
        col_app.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col_app.set_resizable(True)
        col_app.set_min_width(140)
        col_app.set_fixed_width(self.config.col_widths.get(self.config.view_mode, 240))
        col_app.set_expand(False)
        self.col_app = col_app

        self._is_applying_col_width = False
        col_app.connect("notify::width", self._on_col_app_width_changed)

        icon_renderer = Gtk.CellRendererPixbuf()
        icon_renderer.set_property("stock-size", Gtk.IconSize.LARGE_TOOLBAR)
        icon_renderer.set_property("xpad", 4)
        icon_renderer.set_property("ypad", 4)
        col_app.pack_start(icon_renderer, False)
        col_app.add_attribute(icon_renderer, "icon-name", 0)

        name_renderer = Gtk.CellRendererText()
        name_renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        name_renderer.set_property("xpad", 4)
        col_app.pack_start(name_renderer, True)
        col_app.add_attribute(name_renderer, "markup", 1)
        self.tree_view.append_column(col_app)

        col_cats = Gtk.TreeViewColumn(_("Categories"))
        col_cats.set_resizable(True)
        col_cats.set_expand(True)

        cat_renderer = Gtk.CellRendererText()
        cat_renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        cat_renderer.set_property("foreground", "#888888")
        cat_renderer.set_property("xpad", 6)
        col_cats.pack_start(cat_renderer, True)
        col_cats.add_attribute(cat_renderer, "text", 2)
        self.tree_view.append_column(col_cats)
        self.stack.add_named(self.tree_view, "list")

        # Tab 2: CATEGORY
        self.cat_flow = Gtk.FlowBox()
        self.cat_flow.set_valign(Gtk.Align.START)
        self.cat_flow.set_max_children_per_line(4)
        self.cat_flow.set_min_children_per_line(2)
        self.cat_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.cat_flow.set_homogeneous(True)
        self.cat_flow.set_row_spacing(10)
        self.cat_flow.set_column_spacing(10)
        self.stack.add_named(self.cat_flow, "category")

        # Tab 3: GRID
        self.grid_view = LetterGridView(
            on_launch_cb=self.launch_app,
            on_context_menu_cb=self.show_app_context_menu,
            config=self.config,
        )
        self.stack.add_named(self.grid_view, "grid")

        # 3. Footer
        self.footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.footer_box.set_margin_top(2)
        main_box.pack_end(self.footer_box, False, False, 0)

        ver_label = Gtk.Label()
        ver_label.set_markup(
            f"<small><span alpha='55%'>Ver. {APP_VERSION}</span></small>"
        )
        ver_label.set_valign(Gtk.Align.CENTER)
        self.footer_box.pack_end(ver_label, False, False, 0)

    # --- Сворачивание секции All и обновление Pinned ---

    def on_all_header_clicked(self, button):
        if self.active_category_filter is not None or self.search_entry.get_text().strip():
            return
        self.config.all_expanded = not self.config.all_expanded
        self.apply_all_expanded_state()
        self.save_geometry()

    def apply_all_expanded_state(self):
        is_search = bool(self.search_entry.get_text().strip())
        can_collapse = (not is_search) and (self.active_category_filter is None)

        should_show = (not can_collapse) or self.config.all_expanded
        self.stack.set_visible(should_show)
        self.view_btn.set_visible(should_show)

        self.section_arrow.set_visible(can_collapse)
        if can_collapse:
            icon = "pan-down-symbolic" if self.config.all_expanded else "pan-end-symbolic"
            self.section_arrow.set_from_icon_name(icon, Gtk.IconSize.MENU)

    def _on_pinned_changed(self, save_geom=False):
        if save_geom:
            self.save_geometry()
        else:
            is_search = bool(self.search_entry.get_text().strip())
            self.pinned_section.refresh(
                is_searching=is_search,
                in_category=(self.active_category_filter is not None),
            )

    # --- Остальная логика представлений, поиска и данных ---

    def move_app_to_category(self, app_id, target_category):
        if target_category is None:
            self.config.category_overrides.pop(app_id, None)
        elif target_category in CATEGORY_NAMES:
            self.config.category_overrides[app_id] = target_category
        self.config.save_category_overrides()
        self.reload_menu_data()

    def build_view_popover(self):
        popover = Gtk.Popover()
        popover.set_constrain_to(Gtk.PopoverConstraint.NONE)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        box.set_size_request(150, -1)

        self.view_checks = {}
        modes = [
            ("category", _("Category")),
            ("grid", _("Grid")),
            ("list1", _("List 1")),
            ("list2", _("List 2")),
        ]
        for mode_id, title in modes:
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            check_img = Gtk.Image.new_from_icon_name(
                "object-select-symbolic", Gtk.IconSize.MENU
            )
            check_img.set_opacity(1.0 if mode_id == self.config.view_mode else 0.0)
            lbl = Gtk.Label(label=title, xalign=0)
            row_box.pack_start(check_img, False, False, 0)
            row_box.pack_start(lbl, True, True, 0)
            btn.add(row_box)
            btn.connect("clicked", self.on_view_mode_selected, mode_id, popover)
            box.pack_start(btn, False, False, 0)
            self.view_checks[mode_id] = check_img

        box.show_all()
        popover.add(box)
        self.view_btn.set_popover(popover)

    def set_view_mode(self, mode_id):
        self._capture_current_col_width()
        self.config.view_mode = mode_id
        self.active_category_filter = None
        self.back_btn.hide()
        self.section_label.set_text(_("All"))

        titles = {
            "category": _("View: Category"),
            "grid": _("View: Grid"),
            "list1": _("View: List 1"),
            "list2": _("View: List 2"),
        }
        self.view_btn_label.set_text(titles.get(mode_id, _("View: List 1")))

        for mid, img in self.view_checks.items():
            img.set_opacity(1.0 if mid == mode_id else 0.0)

        self.refresh_current_view()
        self.save_geometry()

    def refresh_current_view(self):
        query = self.search_entry.get_text().strip()
        is_search = bool(query)
        in_cat = self.active_category_filter is not None

        self.pinned_section.refresh(is_searching=is_search, in_category=in_cat)

        apps = self.get_filtered_apps()
        if self.config.view_mode == "grid":
            use_breaks = (not is_search) and (not in_cat)
            self.grid_view.populate(apps, use_letter_breaks=use_breaks)
            self.stack.set_visible_child_name("grid")
        elif is_search or in_cat or self.config.view_mode in ("list1", "list2"):
            self.populate_list(apps)
            self.tree_view.show_all()
            self.stack.set_visible_child_name("list")
            self._apply_current_col_width()
        elif self.config.view_mode == "category":
            self.populate_categories(apps)
            self.cat_flow.show_all()
            self.stack.set_visible_child_name("category")

        self.apply_all_expanded_state()

    def on_view_mode_selected(self, button, mode_id, popover):
        popover.popdown()
        self.set_view_mode(mode_id)

    def reload_menu_data(self):
        self.repo.reload()
        self.refresh_current_view()

    def get_filtered_apps(self):
        query = self.search_entry.get_text().strip().casefold()
        apps = self.repo.all_apps

        if self.active_category_filter:
            apps = [a for a in apps if a["category"] == self.active_category_filter]

        if query:
            apps = [
                a
                for a in apps
                if query in a["sort_key"]
                or query in a["comment"].casefold()
                or query in a["categories_str"].casefold()
                or query in a["raw_hint"].casefold()
            ]
        return apps

    def populate_list(self, apps):
        self.list_store.clear()
        self._current_rendered_apps = apps

        use_letter_breaks = (
            self.active_category_filter is None
            and not self.search_entry.get_text().strip()
        )
        last_letter = None

        for idx, app in enumerate(apps):
            if use_letter_breaks:
                first_char = app["name"][:1].upper() if app["name"] else "#"
                if not first_char.isalpha():
                    first_char = "#"
                if first_char != last_letter:
                    last_letter = first_char
                    if self.config.view_mode == "list1":
                        prefix_nl = "\n" if idx > 0 else ""
                        header_markup = (
                            f"{prefix_nl}<b><span size='large'>{GLib.markup_escape_text(first_char)}</span></b>"
                        )
                        self.list_store.append([None, header_markup, "", None, -1, True])
                    elif self.config.view_mode == "list2" and idx > 0:
                        self.list_store.append([None, "<span size='small'> </span>", "", None, -1, True])

            tooltip = (
                f"ID: {app['id']}\n"
                f"{_('File:')} {app['filename']}\n"
                f"{_('Categories:')} {app['raw_hint']}"
            )
            escaped_name = GLib.markup_escape_text(app["name"])
            self.list_store.append(
                [
                    app["icon_name"],
                    escaped_name,
                    app["categories_str"],
                    tooltip,
                    idx,
                    False,
                ]
            )

    def populate_categories(self, apps):
        for child in self.cat_flow.get_children():
            self.cat_flow.remove(child)

        groups = {name: [] for name in CATEGORY_NAMES}
        for app in apps:
            groups[app["category"]].append(app)

        for cat_name in CATEGORY_NAMES:
            cat_apps = groups[cat_name]
            if not cat_apps:
                continue
            card_btn = Gtk.Button()
            card_btn.set_relief(Gtk.ReliefStyle.NONE)
            card_btn.get_style_context().add_class("cat-card")

            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

            mini_grid = Gtk.Grid()
            mini_grid.set_row_spacing(6)
            mini_grid.set_column_spacing(6)
            mini_grid.set_halign(Gtk.Align.CENTER)
            mini_grid.set_valign(Gtk.Align.CENTER)

            for i in range(4):
                if i < len(cat_apps):
                    icon_w = make_icon_widget(cat_apps[i]["icon_name"], 24)
                else:
                    icon_w = Gtk.Box()
                    icon_w.set_size_request(24, 24)
                mini_grid.attach(icon_w, i % 2, i // 2, 1, 1)

            title = Gtk.Label(label=f"{cat_name} ({len(cat_apps)})")
            title.set_max_width_chars(15)
            title.set_ellipsize(Pango.EllipsizeMode.END)

            outer.pack_start(mini_grid, True, True, 2)
            outer.pack_start(title, False, False, 0)
            card_btn.add(outer)
            card_btn.connect("clicked", self.on_category_card_clicked, cat_name)
            self.cat_flow.add(card_btn)

        self.cat_flow.show_all()

    def on_category_card_clicked(self, button, cat_name):
        self._capture_current_col_width()
        self.active_category_filter = cat_name
        self.section_label.set_text(cat_name)
        self.back_btn.show()
        self.refresh_current_view()

    def on_back_to_categories(self, button):
        self._capture_current_col_width()
        self.active_category_filter = None
        self.section_label.set_text(_("All"))
        self.back_btn.hide()
        self.refresh_current_view()

    def on_search_changed(self, entry):
        if entry.get_text().strip():
            self.back_btn.hide()
            self.section_label.set_text(_("Search results"))
        else:
            if self.active_category_filter:
                self.section_label.set_text(self.active_category_filter)
                self.back_btn.show()
            else:
                self.section_label.set_text(_("All"))
                self.back_btn.hide()
        self.refresh_current_view()

    def on_tree_row_activated(self, tree_view, path, column):
        tree_iter = self.list_store.get_iter(path)
        if self.list_store.get_value(tree_iter, 5):
            return
        idx = self.list_store.get_value(tree_iter, 4)
        if 0 <= idx < len(self._current_rendered_apps):
            self.launch_app(self._current_rendered_apps[idx])

    def on_tree_button_press(self, tree_view, event):
        path_info = tree_view.get_path_at_pos(int(event.x), int(event.y))
        if path_info is not None:
            path, col, cell_x, cell_y = path_info
            tree_iter = self.list_store.get_iter(path)
            is_header = self.list_store.get_value(tree_iter, 5)
            if is_header:
                return True

            if event.button == 3:
                tree_view.get_selection().select_path(path)
                idx = self.list_store.get_value(tree_iter, 4)
                if 0 <= idx < len(self._current_rendered_apps):
                    app = self._current_rendered_apps[idx]
                    self.show_app_context_menu(app, event)
                return True
        return False

    def show_app_context_menu(self, app, event):
        menu = Gtk.Menu()

        # Пункт закрепления в Pinned
        is_pinned = self.config.is_pinned(app["id"])
        pin_label = _("Unpin from top") if is_pinned else _("Pin to top")
        pin_item = Gtk.MenuItem(label=pin_label)
        pin_item.connect("activate", lambda w, aid=app["id"]: self._toggle_pin_from_list(aid))
        menu.append(pin_item)
        menu.append(Gtk.SeparatorMenuItem())

        # Смена категории
        header = Gtk.MenuItem(label=_("Move to category:"))
        header.set_sensitive(False)
        menu.append(header)
        menu.append(Gtk.SeparatorMenuItem())

        for cat_name in CATEGORY_NAMES:
            prefix = "● " if app["category"] == cat_name else "    "
            item = Gtk.MenuItem(label=f"{prefix}{_(cat_name)}")
            item.connect(
                "activate",
                lambda w, aid=app["id"], c=cat_name: self.move_app_to_category(aid, c),
            )
            menu.append(item)

        if app["is_manual"]:
            menu.append(Gtk.SeparatorMenuItem())
            reset_item = Gtk.MenuItem(label=_("Reset to automatic"))
            reset_item.connect(
                "activate",
                lambda w, aid=app["id"]: self.move_app_to_category(aid, None),
            )
            menu.append(reset_item)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _toggle_pin_from_list(self, app_id):
        self.config.toggle_pin(app_id)
        self._on_pinned_changed(save_geom=False)

    def launch_app(self, app_dict):
        try:
            app_dict["app_info"].launch([], None)
        except Exception as e:
            print(f"Run error '{app_dict['name']}': {e}", flush=True)
        self.hide_menu()

    # --- Ширина колонок и геометрия ---

    def _on_col_app_width_changed(self, col, param):
        if self._is_applying_col_width:
            return
        if self.stack.get_visible_child_name() != "list":
            return
        cur_w = col.get_width()
        if cur_w >= 140:
            ctx = self._get_active_col_context()
            self.config.col_widths[ctx] = cur_w

    def _capture_current_col_width(self):
        if hasattr(self, "col_app") and self.stack.get_visible_child_name() == "list":
            cur_w = self.col_app.get_width()
            if cur_w >= 140:
                ctx = self._get_active_col_context()
                self.config.col_widths[ctx] = cur_w

    def _apply_current_col_width(self):
        if hasattr(self, "col_app"):
            ctx = self._get_active_col_context()
            target_w = self.config.col_widths.get(ctx, 240)
            self._is_applying_col_width = True
            self.col_app.set_fixed_width(target_w)
            self._is_applying_col_width = False

    def _get_active_col_context(self):
        if self.active_category_filter is not None:
            return "category"
        return self.config.view_mode if self.config.view_mode in ("list1", "list2") else "list1"

    def save_geometry(self):
        width, height = self.get_size()
        self._capture_current_col_width()
        self.config.save_geometry(width, height)

    # --- Ресайз и управление захватом фокуса ---

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
            Gdk.WindowEdge.NORTH_EAST: Gdk.CursorType.TOP_RIGHT_CORNER,
            Gdk.WindowEdge.NORTH_WEST: Gdk.CursorType.TOP_LEFT_CORNER,
            Gdk.WindowEdge.SOUTH_EAST: Gdk.CursorType.BOTTOM_RIGHT_CORNER,
            Gdk.WindowEdge.SOUTH_WEST: Gdk.CursorType.BOTTOM_LEFT_CORNER,
            Gdk.WindowEdge.NORTH: Gdk.CursorType.TOP_SIDE,
            Gdk.WindowEdge.SOUTH: Gdk.CursorType.BOTTOM_SIDE,
            Gdk.WindowEdge.EAST: Gdk.CursorType.RIGHT_SIDE,
            Gdk.WindowEdge.WEST: Gdk.CursorType.LEFT_SIDE,
        }
        cursor_type = cursor_map.get(edge)
        if cursor_type:
            window.set_cursor(Gdk.Cursor.new_for_display(self.get_display(), cursor_type))

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
                None,
            )
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
        if event.x < 0 or event.y < 0 or event.x > alloc.width or event.y > alloc.height:
            self.hide_menu()
            return True

        alt_pressed = bool(event.state & Gdk.ModifierType.MOD1_MASK)
        if alt_pressed and event.button == 3:
            self.start_wm_drag(event, edge=self.get_free_corner_edge())
            return True

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

        is_top = pos in ("n", "nw-h", "ne-h") or "top" in pos
        is_left = pos in ("w", "nw-v", "sw-v") or "left" in pos
        is_right = pos in ("e", "ne-v", "se-v") or "right" in pos

        if is_top:
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
            x = btn_x
            y = btn_y - win_h
            self.expand_v = "north"

        if is_right:
            self.expand_h = "west"
        elif is_left:
            self.expand_h = "east"
        else:
            if wa and (btn_x + win_w > wa.x + wa.width) and (btn_x > wa.x + wa.width // 2):
                x = btn_x + btn_w - win_w
                self.expand_h = "west"
            else:
                self.expand_h = "east"

        if wa:
            x = max(wa.x, min(x, wa.x + wa.width - win_w))
            y = max(wa.y, min(y, wa.y + wa.height - win_h))

        self.move(int(x), int(y))

    def show_and_refresh(self, anchor=None):
        self._capture_current_col_width()
        self.search_entry.set_text("")
        self.active_category_filter = None
        self.back_btn.hide()
        self.section_label.set_text(_("All"))
        self.reload_menu_data()
        self.config.load_geometry()
        self.set_default_size(self.config.width, self.config.height)
        self.resize(self.config.width, self.config.height)
        self._apply_current_col_width()

        if anchor is not None:
            self.position_near_button(*anchor)

        self.show_all()
        if not self.active_category_filter:
            self.back_btn.hide()
        self.refresh_current_view()

        if anchor is not None:
            self.position_near_button(*anchor)

        self.present_with_time(Gdk.CURRENT_TIME)
        self.search_entry.grab_focus()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.active_category_filter:
                self.on_back_to_categories(None)
            else:
                self.hide_menu()
