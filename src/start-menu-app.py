#!/usr/bin/env python3
import os
import sys
import json
import importlib.util
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib


def _register_hyphen_modules():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    modules = [
        "start-menu-app-constants",
        "start-menu-app-config",
        "start-menu-app-data",
        "start-menu-app-pinned",
        "start-menu-app-grid",
        "start-menu-app-window",
    ]
    for mod_file in modules:
        mod_name = mod_file.replace("-", "_")
        path = os.path.join(base_dir, f"{mod_file}.py")
        spec = importlib.util.spec_from_file_location(mod_name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)


_register_hyphen_modules()
from start_menu_app_window import XfceStartMenu


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
