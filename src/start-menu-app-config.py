import json
from pathlib import Path
from gi.repository import GLib
from start_menu_app_constants import CATEGORY_NAMES


class MenuConfigManager:
    def __init__(self):
        self.config_dir = Path(GLib.get_user_config_dir()) / "xfce-start-menu"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.geometry_file = self.config_dir / "geometry.json"
        self.overrides_file = self.config_dir / "category_overrides.json"
        self.pinned_file = self.config_dir / "pinned.json"

        # Состояние по умолчанию
        self.width = 640
        self.height = 520
        self.view_mode = "list1"
        self.col_widths = {"list1": 240, "list2": 240, "category": 240}
        self.all_expanded = True
        self.pinned_expanded = True
        self.icon_size_preset = "normal"
        self.tile_padding_preset = "normal"
        self.label_size_preset = "normal"

        self.category_overrides = self._load_category_overrides()
        self.pinned_ids = self._load_pinned()
        self.load_geometry()

    def load_geometry(self):
        if not self.geometry_file.exists():
            return
        try:
            data = json.loads(self.geometry_file.read_text(encoding="utf-8"))
            self.width = data.get("width", 640)
            self.height = data.get("height", 520)

            saved_mode = data.get("view_mode", "list1")
            if saved_mode == "list":
                saved_mode = "list1"
            if saved_mode in ("list1", "list2", "grid", "category"):
                self.view_mode = saved_mode

            saved_widths = data.get("col_widths")
            if isinstance(saved_widths, dict):
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

            self.all_expanded = bool(data.get("all_expanded", True))
            self.pinned_expanded = bool(data.get("pinned_expanded", True))

            if data.get("icon_size_preset") in ("small", "normal", "large", "huge"):
                self.icon_size_preset = data["icon_size_preset"]
            if data.get("tile_padding_preset") in ("tight", "normal", "relaxed", "wide"):
                self.tile_padding_preset = data["tile_padding_preset"]
            if data.get("label_size_preset") in ("small", "normal", "large", "huge"):
                self.label_size_preset = data["label_size_preset"]
        except Exception as e:
            print(f"Can't read geometry.json: {e}")

    def save_geometry(self, width, height):
        self.width = width
        self.height = height
        data = {
            "width": self.width,
            "height": self.height,
            "view_mode": self.view_mode,
            "col_widths": self.col_widths,
            "all_expanded": self.all_expanded,
            "pinned_expanded": self.pinned_expanded,
            "icon_size_preset": self.icon_size_preset,
            "tile_padding_preset": self.tile_padding_preset,
            "label_size_preset": self.label_size_preset,
        }
        try:
            self.geometry_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Can't save geometry.json: {e}")

    def get_icon_pixel_size(self):
        mapping = {"small": 24, "normal": 32, "large": 40, "huge": 48}
        return mapping.get(self.icon_size_preset, 32)

    def get_tile_spacing(self):
        # (padding_v, padding_h, flowbox_gap, vbox_spacing, max_chars, max_cols)
        mapping = {
            "tight": (1, 1, 1, 1, 7, 12),
            "normal": (3, 2, 3, 2, 8, 10),
            "relaxed": (5, 4, 6, 3, 9, 9),
            "wide": (7, 5, 10, 4, 10, 8),
        }
        return mapping.get(self.tile_padding_preset, (3, 2, 3, 2, 8, 10))

    def get_label_font_css(self):
        mapping = {
            "small": "0.78em",
            "normal": "0.90em",
            "large": "1.05em",
            "huge": "1.18em",
        }
        return mapping.get(self.label_size_preset, "0.90em")

    def _load_category_overrides(self):
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

    def _load_pinned(self):
        if self.pinned_file.exists():
            try:
                data = json.loads(self.pinned_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [str(x) for x in data if isinstance(x, str)]
            except Exception as e:
                print(f"Can't read pinned.json: {e}")
        return []

    def save_pinned(self):
        try:
            self.pinned_file.write_text(
                json.dumps(self.pinned_ids, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"Can't save pinned.json: {e}")

    def is_pinned(self, app_id):
        return app_id in self.pinned_ids

    def toggle_pin(self, app_id):
        if app_id in self.pinned_ids:
            self.pinned_ids.remove(app_id)
        else:
            self.pinned_ids.append(app_id)
        self.save_pinned()

    def move_pinned(self, app_id, delta):
        if app_id not in self.pinned_ids:
            return
        idx = self.pinned_ids.index(app_id)
        new_idx = idx + delta
        if 0 <= new_idx < len(self.pinned_ids):
            self.pinned_ids[idx], self.pinned_ids[new_idx] = (
                self.pinned_ids[new_idx],
                self.pinned_ids[idx],
            )
            self.save_pinned()

    def reorder_pinned(self, src_id, dst_id):
        if (
            src_id == dst_id
            or src_id not in self.pinned_ids
            or dst_id not in self.pinned_ids
        ):
            return
        src_idx = self.pinned_ids.index(src_id)
        dst_idx = self.pinned_ids.index(dst_id)
        item = self.pinned_ids.pop(src_idx)
        self.pinned_ids.insert(dst_idx, item)
        self.save_pinned()
