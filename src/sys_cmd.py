import json
import os
import shlex
import shutil
import subprocess

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

from sys_i18n import _

MAX_HISTORY = 10
MAX_COMPLETIONS = 10
MORE_MARKER = "..."


def _get_history_path():
    cache_base = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    app_cache = os.path.join(cache_base, "xfce-start-menu")
    os.makedirs(app_cache, exist_ok=True)
    return os.path.join(app_cache, "run_history.json")


def _load_history():
    path = _get_history_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(x) for x in data if x][:MAX_HISTORY]
    except (OSError, ValueError):
        pass
    return []


def _save_history(history):
    path = _get_history_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history[:MAX_HISTORY], f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _scan_path_executables():
    """Собирает отсортированный список уникальных исполняемых команд из $PATH."""
    commands = {"cmd"}  # Добавляем виртуальную команду cmd в автодополнение
    path_env = os.environ.get("PATH", "")
    for directory in path_env.split(os.pathsep):
        if not directory or not os.path.isdir(directory):
            continue
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file() and os.access(entry.path, os.X_OK):
                        commands.add(entry.name)
        except OSError:
            continue
    return sorted(commands)

def _get_xfce_terminal():
    """Читает выбранный в XFCE эмулятор терминала из helpers.rc или ищет в PATH."""
    helpers_rc = os.path.expanduser("~/.config/xfce4/helpers.rc")
    if os.path.isfile(helpers_rc):
        try:
            with open(helpers_rc, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("TerminalEmulator="):
                        term = line.split("=", 1)[ 1 ].strip()
                        # В helpers.rc бывает 'debian-x-terminal-emulator' -> x-terminal-emulator
                        if term == "debian-x-terminal-emulator":
                            term = "x-terminal-emulator"
                        if shutil.which(term):
                            return term
        except OSError:
            pass

    for candidate in ("xfce4-terminal", "gnome-terminal", "x-terminal-emulator", "xterm"):
        if shutil.which(candidate):
            return candidate
    return "xterm"


def _get_xfce_terminal():
    """Читает выбранный в XFCE эмулятор терминала из helpers.rc или ищет в PATH."""
    helpers_rc = os.path.expanduser("~/.config/xfce4/helpers.rc")
    if os.path.isfile(helpers_rc):
        try:
            with open(helpers_rc, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("TerminalEmulator="):
                        term = line.split("=", 1)[ 1 ].strip()
                        # В helpers.rc бывает 'debian-x-terminal-emulator' -> x-terminal-emulator
                        if term == "debian-x-terminal-emulator":
                            term = "x-terminal-emulator"
                        if shutil.which(term):
                            return term
        except OSError:
            pass

    for candidate in ("xfce4-terminal", "gnome-terminal", "x-terminal-emulator", "xterm"):
        if shutil.which(candidate):
            return candidate
    return "xterm"


def _resolve_virtual_command(args):
    """
    Обрабатывает виртуальную команду 'cmd' -> системный терминал XFCE.
    Поддерживает как чистый вызов 'cmd', так и 'cmd <команда>'.
    """
    if not args or args[ 0 ] != "cmd":
        return args

    term = _get_xfce_terminal()
    if len(args) == 1:
        return [term]

    # Для gnome-terminal (и обёртки x-terminal-emulator над ним) используем '--'
    real_bin = os.path.basename(os.path.realpath(shutil.which(term) or term))
    if "gnome-terminal" in real_bin:
        return [term, "--"] + args[ 1: ]

    sub_cmd = " ".join(shlex.quote(a) for a in args[ 1: ])
    return [term, "-e", f"sh -c {shlex.quote(sub_cmd)}"]


class RunDialog(Gtk.Dialog):
    def __init__(self, anchor=None):
        super().__init__(title=_("Run"))
        self.anchor = anchor
        self.set_default_size(420, -1)
        self.set_resizable(False)
        self.set_icon_name("system-run")

        self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        run_btn = self.add_button(_("Run"), Gtk.ResponseType.OK)
        run_btn.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)

        content = self.get_content_area()
        content.set_border_width(12)
        content.set_spacing(10)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        icon = Gtk.Image.new_from_icon_name("system-run", Gtk.IconSize.DIALOG)
        label = Gtk.Label(
            label=_("Type the name of a program, folder, or command to run:"),
            xalign=0,
        )
        label.set_line_wrap(True)
        header_box.pack_start(icon, False, False, 0)
        header_box.pack_start(label, True, True, 0)
        content.pack_start(header_box, False, False, 0)

        self.history = _load_history()
        self.combo = Gtk.ComboBoxText.new_with_entry()
        for cmd in self.history:
            self.combo.append_text(cmd)

        self.entry = self.combo.get_child()
        self.entry.set_activates_default(True)
        self.entry.set_placeholder_text(_("Command... (Tab to complete)"))
        if self.history:
            self.entry.set_text(self.history[ 0 ])
            self.entry.select_region(0, -1)

        content.pack_start(self.combo, False, False, 0)

        # Модель автодополнения: (отображаемый_текст, is_more_marker)
        self.all_commands = _scan_path_executables()
        self.completion_store = Gtk.ListStore(str, bool)
        self.completion = Gtk.EntryCompletion()
        self.completion.set_model(self.completion_store)
        self.completion.set_text_column(0)
        self.completion.set_inline_completion(False)
        self.completion.set_popup_completion(True)
        self.completion.set_minimum_key_length(3)
        self.completion.set_match_func(lambda *args: True, None)
        self.completion.connect("match-selected", self._on_match_selected)
        self.entry.set_completion(self.completion)

        self.entry.connect("changed", self._on_entry_changed)
        self.entry.connect("key-press-event", self._on_key_press)

        self.connect("map-event", lambda w, e: self._position_near_anchor())
        self.show_all()
        self._position_near_anchor()


    def _position_near_anchor(self):
        """Размещает окно строго над/рядом с панелью с учётом высоты заголовка окна."""
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geom = monitor.get_geometry()

        _, nat_w = self.get_preferred_width()
        _, nat_h = self.get_preferred_height()
        win_w = max(nat_w, 420)
        # Добавляем высоту заголовка окна (~36px), если рамка ещё не отрисована
        gdk_win = self.get_window()
        if gdk_win:
            frame = gdk_win.get_frame_extents()
            win_w = max(frame.width, nat_w + 10)
            win_h = max(frame.height, nat_h + 36)
        else:
            win_w = max(nat_w, 420) + 10
            win_h = nat_h + 36

        margin = 10

        if self.anchor:
            btn_x, btn_y, btn_w, btn_h, pos_name = self.anchor
            pos = pos_name.lower()
            if pos in ("n", "nw-h", "ne-h"):  # Панель сверху
                x = btn_x
                y = btn_y + btn_h + margin
            elif pos in ("w", "nw-v", "sw-v"):  # Панель слева — выравниваем по уровню кнопки
                x = btn_x + btn_w + margin
                y = btn_y
            elif pos in ("e", "ne-v", "se-v"):  # Панель справа — выравниваем по уровню кнопки
                x = btn_x - win_w - margin
                y = btn_y
            else:  # Панель снизу (по умолчанию)
                x = btn_x
                y = btn_y - win_h - margin
        else:
            workarea = monitor.get_workarea()
            x = workarea.x + margin
            y = workarea.y + workarea.height - win_h - margin

        x = max(geom.x + margin, min(x, geom.x + geom.width - win_w - margin))
        y = max(geom.y + margin, min(y, geom.y + geom.height - win_h - margin))
        self.move(x, y)


    def _get_matches(self, prefix):
        """Возвращает (список_до_10_команд, есть_ли_ещё)."""
        if not prefix:
            return [], False
        all_matches = [c for c in self.all_commands if c.startswith(prefix)]
        has_more = len(all_matches) > MAX_COMPLETIONS
        return all_matches[:MAX_COMPLETIONS], has_more

    def _update_suggestions(self, text):
        self.completion_store.clear()
        if not text or " " in text:
            return
        matches, has_more = self._get_matches(text)
        for cmd in matches:
            self.completion_store.append([cmd, False])
        if has_more:
            self.completion_store.append([MORE_MARKER, True])

    def _on_match_selected(self, completion, model, tree_iter):
        is_more = model.get_value(tree_iter, 1)
        if is_more:
            # Клик по "..." не затирает уже набранный пользователем префикс
            return True
        return False

    def _on_entry_changed(self, entry):
        text = entry.get_text()
        if len(text) >= 3:
            self._update_suggestions(text)
        else:
            self.completion_store.clear()

    def _on_key_press(self, widget, event):
        if event.keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            text = self.entry.get_text()
            if not text or " " in text:
                return False

            matches, _ = self._get_matches(text)
            if not matches:
                return True

            if len(matches) == 1:
                self.entry.set_text(matches[ 0 ])
                self.entry.set_position(-1)
                self.completion_store.clear()
            else:
                common = os.path.commonprefix(matches)
                if len(common) > len(text):
                    self.entry.set_text(common)
                    self.entry.set_position(-1)
                self._update_suggestions(self.entry.get_text())
                self.completion.complete()

            return True
        return False

    def _record_history(self, cmd):
        new_hist = [cmd] + [item for item in self.history if item != cmd]
        self.history = new_hist[:MAX_HISTORY]
        _save_history(self.history)

    def execute_current(self):
        raw_cmd = self.entry.get_text().strip()
        if not raw_cmd:
            return True

        try:
            args = shlex.split(raw_cmd)
            exec_args = _resolve_virtual_command(args)
            subprocess.Popen(exec_args, start_new_session=True)
            self._record_history(raw_cmd)
            return True
        except Exception as e:
            err_dlg = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_("Failed to run '{cmd}'").format(cmd=raw_cmd),
            )
            err_dlg.set_title(_("Run"))
            err_dlg.format_secondary_text(str(e))
            err_dlg.run()
            err_dlg.destroy()
            return False

def show_run_dialog(anchor=None):
    """Точка входа для вызова диалога Run из меню или по хоткею."""
    dialog = RunDialog(anchor=anchor)
    while True:
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            if dialog.execute_current():
                break
        else:
            break
    dialog.destroy()

