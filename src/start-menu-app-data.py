import os
from gi.repository import Gio, Gtk, GdkPixbuf
from start_menu_app_constants import IGNORED_CATEGORIES, FIXED_CATEGORIES, _


class AppRepository:
    def __init__(self, config):
        self.config = config
        self.all_apps = []
        self.apps_by_id = {}

    def resolve_single_category(self, app_id, clean_cats):
        if app_id in self.config.category_overrides:
            return self.config.category_overrides[app_id], True

        lower_set = {c.casefold() for c in clean_cats}
        for cat_name, keywords in FIXED_CATEGORIES:
            if lower_set & keywords:
                return cat_name, False

        return "Other", False

    def reload(self):
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
                    icon_name = names[0]
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

        self.apps_by_id = unique_map
        self.all_apps = sorted(unique_map.values(), key=lambda x: x["sort_key"])
        return self.all_apps

    def get_pinned_apps(self):
        result = []
        for app_id in self.config.pinned_ids:
            if app_id in self.apps_by_id:
                result.append(self.apps_by_id[app_id])
        return result


def make_icon_widget(icon_name, pixel_size):
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
