import os
import gi
import json
import sys
import gettext
import locale
import subprocess

gi.require_version("Gtk", "3.0")
from pathlib import Path
from gi.repository import Gtk, Gdk, GLib, Gio, Pango, GdkPixbuf


APP_DOMAIN = "xfce-start-menu"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_LOCALE_DIR = os.path.join(BASE_DIR, "locale")
SYS_LOCALE_DIR = "/usr/share/locale"
LOCALE_DIR = LOCAL_LOCALE_DIR if os.path.isdir(LOCAL_LOCALE_DIR) else SYS_LOCALE_DIR

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

_translation = gettext.translation(APP_DOMAIN, localedir=LOCALE_DIR, fallback=True)
_ = _translation.gettext


IGNORED_CATEGORIES = {
    "xfce",
    "x-xfce",
    "x-xfce-settingsdialog",
    "x-xfce-personalsettings",
    "x-xfce-hardwaresettings",
    "x-xfce-systemsettings",
    "x-xfce-toplevel",
    "gnome",
    "kde",
    "mate",
    "lxde",
    "lxqt",
    "cinnamon",
    "pantheon",
    "gtk",
    "qt",
    "motif",
    "java",
    "consoleonly",
    "application",
    "core",
    "x-red-hat-base",
    "x-suse-core-system",
    "x-debian-applications",
}

# Порядок важен: более специфичные категории проверяются раньше общих (Utility/System)
FIXED_CATEGORIES = [
    (
        "Terminal",
        {
            "terminalemulator",
            "x-debug-applications-shell",
            "x-debian-applications-shell",
            "x-debian-applications-shells",
        },
    ),
    (
        "Development",
        {
            "development",
            "ide",
            "debugger",
            "revisioncontrol",
            "profiling",
            "translation",
            "guidesigner",
            "database",
            "webdevelopment",
        },
    ),
    (
        "Games",
        {
            "game",
            "actiongame",
            "adventuregame",
            "arcadegame",
            "boardgame",
            "cardgame",
            "logicgame",
            "roleplaying",
            "simulation",
            "sportsgame",
            "strategygame",
        },
    ),
    (
        "Graphics & Design",
        {
            "graphics",
            "2dgraphics",
            "3dgraphics",
            "vectorgraphics",
            "rastergraphics",
            "photography",
            "scanning",
            "publishing",
        },
    ),
    (
        "Multimedia",
        {
            "audiovideo",
            "audio",
            "video",
            "player",
            "recorder",
            "midi",
            "mixer",
            "sequencer",
            "tuner",
            "tv",
            "discburning",
        },
    ),
    (
        "Internet & Network",
        {
            "network",
            "webbrowser",
            "email",
            "instantmessaging",
            "filetransfer",
            "remoteaccess",
            "p2p",
            "ircclient",
            "news",
        },
    ),
    (
        "Office & Productivity",
        {
            "office",
            "wordprocessor",
            "spreadsheet",
            "presentation",
            "calendar",
            "contactmanagement",
            "viewer",
            "texteditor",
            "finance",
            "projectmanagement",
        },
    ),
    (
        "Education & Science",
        {
            "education",
            "science",
            "math",
            "astronomy",
            "biology",
            "chemistry",
            "physics",
            "engineering",
            "electronics",
            "geography",
            "languages",
        },
    ),
    (
        "System",
        {
            "system",
            "monitor",
            "packagemanager",
            "filesystem",
            "security",
            "emulator",
            "settings",
            "hardwaresettings",
            "desktopsettings",
        },
    ),
    (
        "Utilities",
        {
            "utility",
            "archiving",
            "compression",
            "filetools",
            "filemanager",
            "calculator",
            "clock",
            "accessibility",
            "texttools",
        },
    ),
    ("Other", set()),
]


CATEGORY_NAMES = [name for name, _ in FIXED_CATEGORIES]


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

        config_dir = Path(GLib.get_user_config_dir()) / "xfce-start-menu"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = config_dir / "geometry.json"

        self.overrides_file = config_dir / "category_overrides.json"
        self.category_overrides = self.load_category_overrides()

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

        self.view_mode = "list1"
        self.col_widths = {
            "list1": 240,
            "list2": 240,
            "category": 240,
        }
        self.active_category_filter = None
        self.all_apps = []
        self._current_rendered_apps = []

        self.load_geometry()
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
        css = b"""
        window {
            border: 1px solid @borders;
        }
        .section-title {
            font-weight: bold;
            font-size: 1.05em;
        }
        .view-btn {
            padding: 2px 8px;
        }
        .cat-card {
            background-color: alpha(@theme_fg_color, 0.04);
            border: 1px solid alpha(@borders, 0.5);
            border-radius: 10px;
            padding: 10px;
        }
        .cat-card:hover {
            background-color: alpha(@theme_fg_color, 0.09);
        }
        .grid-item {
            border-radius: 8px;
            padding: 6px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(14)
        main_box.set_margin_end(14)
        self.add(main_box)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Search for apps..."))
        self.search_entry.connect("search-changed", self.on_search_changed)
        main_box.pack_start(self.search_entry, False, False, 0)

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

        self.section_label = Gtk.Label(label=_("All"), xalign=0)
        self.section_label.get_style_context().add_class("section-title")
        header_box.pack_start(self.section_label, True, True, 0)

        self.view_btn = Gtk.MenuButton()
        self.view_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.view_btn.get_style_context().add_class("view-btn")
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.view_btn_label = Gtk.Label(label=_("View: List"))
        arrow = Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.MENU)
        btn_box.pack_start(self.view_btn_label, False, False, 0)
        btn_box.pack_start(arrow, False, False, 0)
        self.view_btn.add(btn_box)

        self.build_view_popover()
        header_box.pack_end(self.view_btn, False, False, 0)
        main_box.pack_start(header_box, False, False, 0)

        titles = {
            "category": _("View: Category"),
            "list1": _("View: List 1"),
            "list2": _("View: List 2"),
        }
        self.view_btn_label.set_text(titles.get(self.view_mode, _("View: List 1")))


        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.pack_start(self.scroll, True, True, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        self.scroll.add(self.stack)

        # --- Tab 1: LIST ---
        # Columns: 0=icon_name, 1=markup_or_name, 2=categories_str, 3=tooltip, 4=app_index, 5=is_header
        self.list_store = Gtk.ListStore(str, str, str, str, int, bool)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_headers_visible(True)
        self.tree_view.set_activate_on_single_click(True)
        self.tree_view.set_tooltip_column(3)
        self.tree_view.connect("row-activated", self.on_tree_row_activated)
        self.tree_view.connect("button-press-event", self.on_tree_button_press)

        selection = self.tree_view.get_selection()
        selection.set_select_function(
            lambda sel, model, path, path_currently_selected, data: not model.get_value(model.get_iter(path), 5),
            None
        )

        col_app = Gtk.TreeViewColumn(_("Application"))
        col_app.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col_app.set_resizable(True)
        col_app.set_min_width(140)
        col_app.set_fixed_width(self.col_widths.get(self.view_mode, 240))
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

        # --- Tab 2: CATEGORY ---
        self.cat_flow = Gtk.FlowBox()
        self.cat_flow.set_valign(Gtk.Align.START)
        self.cat_flow.set_max_children_per_line(4)
        self.cat_flow.set_min_children_per_line(2)
        self.cat_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.cat_flow.set_homogeneous(True)
        self.cat_flow.set_row_spacing(10)
        self.cat_flow.set_column_spacing(10)

        self.stack.add_named(self.cat_flow, "category")

        # 4. Footer
        self.footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.footer_box.set_margin_top(2)
        main_box.pack_end(self.footer_box, False, False, 0)

        ver_label = Gtk.Label()
        ver_label.set_markup(
            f"<small><span alpha='55%'>Ver. {APP_VERSION}</span></small>"
        )
        ver_label.set_valign(Gtk.Align.CENTER)
        self.footer_box.pack_end(ver_label, False, False, 0)

    def load_category_overrides(self):
        if self.overrides_file.exists():
            try:
                data = json.loads(self.overrides_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {k: v for k, v in data.items() if v in CATEGORY_NAMES}
            except Exception as e:
                print(f"Can't read category_overrides.json: {e}")
        return {}

    def save_category_overrides(self):
        try:
            self.overrides_file.write_text(
                json.dumps(self.category_overrides, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"Can't save category_overrides.json: {e}")

    def resolve_single_category(self, app_id, clean_cats):
        # 1. Проверяем ручное переопределение из конфига
        if app_id in self.category_overrides:
            return self.category_overrides[app_id], True

        # 2. Автоматический подбор строго одной категории по приоритету
        lower_set = {c.casefold() for c in clean_cats}
        for cat_name, keywords in FIXED_CATEGORIES:
            if lower_set & keywords:
                return cat_name, False

        return "Other", False

    def move_app_to_category(self, app_id, target_category):
        if target_category is None:
            self.category_overrides.pop(app_id, None)
        elif target_category in CATEGORY_NAMES:
            self.category_overrides[app_id] = target_category
        self.save_category_overrides()
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
            check_img.set_opacity(1.0 if mode_id == self.view_mode else 0.0)
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
        self.view_mode = mode_id
        self.active_category_filter = None
        self.back_btn.hide()
        self.section_label.set_text(_("All"))

        titles = {
            "category": _("View: Category"),
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
        apps = self.get_filtered_apps()

        if query or self.active_category_filter is not None or self.view_mode in ("list1", "list2"):
            self.populate_list(apps)
            self.tree_view.show_all()
            self.stack.set_visible_child_name("list")
            self._apply_current_col_width()
        elif self.view_mode == "category":
            self.populate_categories(apps)
            self.cat_flow.show_all()
            self.stack.set_visible_child_name("category")

    def on_view_mode_selected(self, button, mode_id, popover):
        popover.popdown()
        self.set_view_mode(mode_id)

    def reload_menu_data(self):
        raw_apps = Gio.AppInfo.get_all()
        unique_map = {}

        for info in raw_apps:
            if not isinstance(info, Gio.DesktopAppInfo):
                continue
            if not info.should_show():
                continue

            app_id = info.get_id() or info.get_name()
            if not app_id or app_id in unique_map:
                continue

            name = (info.get_name() or "").strip()
            if not name:
                continue

            cats_raw = info.get_categories() or ""
            clean_cats = [
                c.strip()
                for c in cats_raw.split(";")
                if c.strip() and c.strip().casefold() not in IGNORED_CATEGORIES
            ]
            assigned_cat, is_manual = self.resolve_single_category(app_id, clean_cats)
            raw_hint = ", ".join(clean_cats) if clean_cats else "—"
            col2_text = f"{assigned_cat}{'*' if is_manual else ''}"

            gicon = info.get_icon()
            icon_name = "application-x-executable"
            if isinstance(gicon, Gio.ThemedIcon):
                names = gicon.get_names()
                if names:
                    icon_name = names[ 0 ]
            elif isinstance(gicon, Gio.FileIcon):
                icon_name = gicon.get_file().get_path() or icon_name

            filename = info.get_filename() or _("Path not found")
            comment = info.get_description() or ""

            unique_map[app_id] = {
                "id": app_id,
                "name": name,
                "sort_key": name.casefold(),
                "comment": comment,
                "categories": clean_cats,
                "raw_hint": raw_hint,
                "category": assigned_cat,
                "is_manual": is_manual,
                "categories_str": col2_text,
                "icon_name": icon_name,
                "filename": filename,
                "app_info": info,
            }

        self.all_apps = sorted(unique_map.values(), key=lambda x: x["sort_key"])
        self.refresh_current_view()

    def get_filtered_apps(self):
        query = self.search_entry.get_text().strip().casefold()
        apps = self.all_apps

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
                    if self.view_mode == "list1":
                        prefix_nl = "\n" if idx > 0 else ""
                        header_markup = (
                            f"{prefix_nl}<b><span size='large'>{GLib.markup_escape_text(first_char)}</span></b>"
                        )
                        self.list_store.append([None, header_markup, "", None, -1, True])
                    elif self.view_mode == "list2" and idx > 0:
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
                    icon_w = self._make_icon_widget(cat_apps[i]["icon_name"], 24)
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

    def _make_icon_widget(self, icon_name, pixel_size):
        if os.path.isabs(icon_name) and os.path.exists(icon_name):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_name, pixel_size, pixel_size, True
                )
                return Gtk.Image.new_from_pixbuf(pb)
            except Exception:
                pass
        img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
        img.set_pixel_size(pixel_size)
        return img

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
        if self.list_store.get_value(tree_iter, 5):  # это строка-заголовок буквы
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

            # Полностью глушим любой клик (ЛКМ и ПКМ) по букве или линии-разделителю
            if is_header:
                return True

            if event.button == 3:  # ПКМ по приложению
                tree_view.get_selection().select_path(path)
                idx = self.list_store.get_value(tree_iter, 4)
                if 0 <= idx < len(self._current_rendered_apps):
                    app = self._current_rendered_apps[idx]
                    self.show_move_category_menu(app, event)
                return True
        return False

    def show_move_category_menu(self, app, event):
        menu = Gtk.Menu()
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

    def launch_app(self, app_dict):
        try:
            app_dict["app_info"].launch([], None)
        except Exception as e:
            print(f"Run error '{app_dict['name']}': {e}", flush=True)
        self.hide_menu()

    def _on_col_app_width_changed(self, col, param):
        if self._is_applying_col_width:
            return
        if self.stack.get_visible_child_name() != "list":
            return
        cur_w = col.get_width()
        if cur_w >= 140:
            ctx = self._get_active_col_context()
            self.col_widths[ctx] = cur_w

    def _capture_current_col_width(self):
        if hasattr(self, "col_app") and self.stack.get_visible_child_name() == "list":
            cur_w = self.col_app.get_width()
            if cur_w >= 140:
                ctx = self._get_active_col_context()
                self.col_widths[ctx] = cur_w

    def _apply_current_col_width(self):
        if hasattr(self, "col_app"):
            ctx = self._get_active_col_context()
            target_w = self.col_widths.get(ctx, 240)
            self._is_applying_col_width = True
            self.col_app.set_fixed_width(target_w)
            self._is_applying_col_width = False

    def _get_active_col_context(self):
        if self.active_category_filter is not None:
            return "category"
        return self.view_mode if self.view_mode in ("list1", "list2") else "list1"

    def load_geometry(self):
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                w = data.get("width", 640)
                h = data.get("height", 520)
                saved_mode = data.get("view_mode", "list1")
                if saved_mode == "list":
                    saved_mode = "list1"
                if saved_mode in ("list1", "list2", "category"):
                    self.view_mode = saved_mode

                saved_widths = data.get("col_widths")
                if isinstance(saved_widths, dict):
                    # Обратная совместимость со старым ключом "list"
                    if "list" in saved_widths and isinstance(saved_widths["list"], int):
                        self.col_widths["list1"] = saved_widths["list"]
                        self.col_widths["list2"] = saved_widths["list"]
                    for k in ("list1", "list2", "category"):
                        w_val = saved_widths.get(k)
                        if isinstance(w_val, int) and w_val >= 140:
                            self.col_widths[k] = w_val
                elif (
                    isinstance(data.get("app_col_width"), int)
                    and data["app_col_width"] >= 140
                ):
                    for k in ("list1", "list2", "category"):
                        self.col_widths[k] = data["app_col_width"]

                self.set_default_size(w, h)
                self.resize(w, h)
                return
            except Exception as e:
                print(f"Can't read geometry: {e}")
        self.set_default_size(640, 520)


    def save_geometry(self):
        try:
            width, height = self.get_size()
            self._capture_current_col_width()

            data = {
                "width": width,
                "height": height,
                "view_mode": self.view_mode,
                "col_widths": self.col_widths,
            }
            self.config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Can't save geometry: {e}")

    def get_resize_edge(self, x, y):
        alloc = self.get_allocation()
        margin = 8
        on_free_h = (
            (x >= alloc.width - margin) if self.expand_h == "east" else (x <= margin)
        )
        on_free_v = (
            (y <= margin) if self.expand_v == "north" else (y >= alloc.height - margin)
        )

        if on_free_h and on_free_v:
            if self.expand_v == "north" and self.expand_h == "east":
                return Gdk.WindowEdge.NORTH_EAST
            elif self.expand_v == "north" and self.expand_h == "west":
                return Gdk.WindowEdge.NORTH_WEST
            elif self.expand_v == "south" and self.expand_h == "east":
                return Gdk.WindowEdge.SOUTH_EAST
            return Gdk.WindowEdge.SOUTH_WEST
        elif on_free_h:
            return (
                Gdk.WindowEdge.EAST if self.expand_h == "east" else Gdk.WindowEdge.WEST
            )
        elif on_free_v:
            return (
                Gdk.WindowEdge.NORTH
                if self.expand_v == "north"
                else Gdk.WindowEdge.SOUTH
            )
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
            window.set_cursor(
                Gdk.Cursor.new_for_display(self.get_display(), cursor_type)
            )

    def on_leave_notify(self, widget, event):
        if (
            event.mode == Gdk.CrossingMode.NORMAL
            and event.detail != Gdk.NotifyType.INFERIOR
        ):
            window = self.get_window()
            if window:
                window.set_cursor(None)
                default_cursor = Gdk.Cursor.new_for_display(
                    self.get_display(), Gdk.CursorType.LEFT_PTR
                )
                self.grab_seat(event, cursor=default_cursor)
        return False

    def on_enter_notify(self, widget, event):
        if (
            event.mode == Gdk.CrossingMode.NORMAL
            and event.detail != Gdk.NotifyType.INFERIOR
        ):
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
        if (
            event.x < 0
            or event.y < 0
            or event.x > alloc.width
            or event.y > alloc.height
        ):
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
            if wa and (
                (btn_y + win_h > wa.y + wa.height) or (btn_y > wa.y + wa.height // 2)
            ):
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
            if (
                wa
                and (btn_x + win_w > wa.x + wa.width)
                and (btn_x > wa.x + wa.width // 2)
            ):
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
        self.load_geometry()
        self._apply_current_col_width()

        if anchor is not None:
            self.position_near_button(*anchor)

        self.show_all()
        if not self.active_category_filter:
            self.back_btn.hide()

        if anchor is not None:
            self.position_near_button(*anchor)
        else:
            self.load_geometry()

        self.present_with_time(Gdk.CURRENT_TIME)
        self.search_entry.grab_focus()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            if self.active_category_filter:
                self.on_back_to_categories(None)
            else:
                self.hide_menu()


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
