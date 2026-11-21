# Xfce Start Menu

Modern Start button and Windows 11–style Quick Link (`Win+X`) system menu for the **Xfce4 Panel**, built with **Python 3**, **GTK 3 / GLib**, and a lightweight **C (`libxfce4panel`)** wrapper.

> **Status:** Active MVP (Minimum Viable Product)

---

## Features & Highlights

* **Dual-Action Panel Button:**
  * **Left-click (`Win`)** — opens the main Applications Menu (`start-menu-app.py` via D-Bus or standalone fallback).
  * **Right-click (`Win+X`)** — opens the Windows 11–inspired **System Menu** (`sys_winx_menu.py`) with quick access to system tools, terminals, task manager, settings, and power actions.
  * **Shift + Right-click** — opens standard Xfce Panel item preferences.
* **Layout-Independent `Win+X` Navigation:**
  * Supports single-key accelerators inside the open `Win+X` menu (e.g., `Win+X, I` for Terminal, `Win+X, A` for Terminal Admin, `Win+X, U → R` for Restart).
  * Works regardless of active keyboard layout (Latin, Cyrillic, etc.) or CapsLock/Shift state via `Gdk.Keymap` translation.
  * User-customizable keybindings stored in `~/.config/xfce-start-menu/winx_keys.json` (auto-generated on first launch).
* **Automatic Global Hotkey Management (`xfconf`):**
  * Automatically registers and validates global shortcuts (`Win`, `Win+X`, `Win+I`, `Win+S`, `Win+E`, `Win+R`, `Win+D`, `Ctrl+Shift+Esc`) in `xfce4-keyboard-shortcuts`.
  * Detects conflicting system bindings and prompts the user with options to fix automatically, open **Xfce Keyboard Settings**, or keep current settings.
* **Custom `Run` Dialog (`Win+R`):**
  * Built-in `Run` dialog (`sys_cmd.py`) positioned relative to the panel edge (top, bottom, left, or right).
  * Features `$PATH` executable autocomplete (`Tab`), persistent command history (`~/.cache/xfce-start-menu/run_history.json`), and a virtual `cmd` alias that launches the user's preferred Xfce terminal.
* **Smart Delayed Tooltips & On-Demand Package Helper:**
  * Native GTK tooltips appear after a 3-second hover delay, displaying both global shortcuts and `Win+X` key sequences (`Win+E  |  Win+X, E`).
  * Missing optional utilities (e.g., `gnome-disks`, `hardinfo2`) are marked with `[!]` and offer one-click installation via `apt` in a terminal window.
* **Internationalization (`gettext`):**
  * Full `i18n` pipeline (`pot` / `po` / `mo` + localized `.desktop` file) with English (`en_US`) and Russian (`ru_RU`) support out of the box.

---

## Architecture Overview

| Component | Role |
| :--- | :--- |
| `src/start-menu.c` | Lightweight C wrapper (`libstartmenu.so`) embedding Python 3 into `xfce4-panel`. |
| `src/start-menu-sys.py` | Panel plugin entry point, panel sizing/anchoring, D-Bus trigger, and `remote-event` router. |
| `src/start-menu-app.py` | Main Start / Applications menu window (`org.custom.xfce.startmenu`). |
| `src/sys_winx_menu.py` | `Win+X` popup menu builder, JSON keymap loader, layout-agnostic key handler, and delayed tooltips. |
| `src/sys_shortcuts.py` | Single Source of Truth for global Xfce shortcuts, drift detection, and interactive `xfconf` repair. |
| `src/sys_actions.py` | Action resolver, startup notification timestamping (`DESKTOP_STARTUP_ID`), and `apt` installer helper. |
| `src/sys_cmd.py` | Custom `Run` (`Win+R`) dialog with `$PATH` completion and command history. |
| `src/sys_i18n.py` | `gettext` initialization and version loader (`VERSION`). |

---

## Prerequisites

### Debian / Ubuntu / Linux Mint
```bash
sudo apt update
sudo apt install build-essential libxfce4panel-2.0-dev python3-dev python3-gi python3-gi-dev \
                 gir1.2-gtk-3.0 gir1.2-garcon-1.0 gir1.2-wnck-3.0 gettext
```

### Fedora / RHEL / openSUSE
```bash
sudo dnf install gcc make xfce4-panel-devel python3-devel python3-gobject \
                 gtk3 garcon libwnck3 gettext
```

---

## Build & Installation

The `Makefile` automatically detects your distribution and architecture (`x86_64`, `aarch64`, etc.) to select the proper plugin library path (`/usr/lib/<arch>-linux-gnu/xfce4/panel/plugins` on Debian/Ubuntu, `/usr/lib64/xfce4/panel/plugins` on Fedora/SUSE, or `/usr/lib/xfce4/panel/plugins` on Arch).

1. **Build the C wrapper, update translations, and generate the `.desktop` file:**
   ```bash
   make all
   ```
   *(Or run individual targets: `make plugin`, `make pot`, `make po`, `make mo`, `make desktop`)*

2. **Install system-wide:**
   ```bash
   sudo make install
   ```

3. **Restart the Xfce panel and add the plugin:**
   ```bash
   xfce4-panel -r
   ```
   Right-click your Xfce Panel → **Panel → Add New Items...** → select **Start Menu** and move it to the desired corner.

4. **Uninstall (if needed):**
   ```bash
   sudo make uninstall
   ```

---

## Configuration

### 1. Global Shortcuts (`xfce4-keyboard-shortcuts`)
On startup or when opening the `Win+X` menu, the plugin automatically checks `xfce4-keyboard-shortcuts` and offers to register the standard bindings:

| Action | Global Shortcut | Panel Event Command |
| :--- | :--- | :--- |
| Applications Menu | `Win` (`Super_L`) | `xfce4-panel --plugin-event=start-menu:start:bool:true` |
| System Menu (`Win+X`) | `Win + X` | `xfce4-panel --plugin-event=start-menu:winx:bool:true` |
| Settings | `Win + I` | `xfce4-panel --plugin-event=start-menu:settings:bool:true` |
| File Explorer | `Win + E` | `xfce4-panel --plugin-event=start-menu:file_explorer:bool:true` |
| Search | `Win + S` | `xfce4-panel --plugin-event=start-menu:search:bool:true` |
| Run Dialog | `Win + R` | `xfce4-panel --plugin-event=start-menu:run:bool:true` |
| Task Manager | `Ctrl + Shift + Esc` | `xfce4-panel --plugin-event=start-menu:task_manager:bool:true` |
| Show Desktop | `Win + D` | `xfce4-panel --plugin-event=start-menu:desktop:bool:true` |

> **Note:** If you have multiple instances of the plugin on your panel, check the exact plugin ID via `xfconf-query -c xfce4-panel -p /plugins -l -v | grep start-menu` (e.g., `start-menu-14`).

### 2. Customizing `Win+X` Menu Keys
On first launch, the plugin generates `~/.config/xfce-start-menu/winx_keys.json` with Windows 11 default keys (`F`, `O`, `V`, `Y`, `M`, `W`, `K`, `G`, `I`, `A`, `T`, `N`, `E`, `S`, `R`, `U`, `D`). Edit this file to remap any menu key without modifying source code.

---

## Troubleshooting & Debug

```bash
# Find active start-menu plugin ID on the panel
xfconf-query -c xfce4-panel -p /plugins -l -v | grep start-menu

# Inspect registered Super / Esc shortcuts in xfconf
xfconf-query -c xfce4-keyboard-shortcuts -l -v | grep -iE "super|Primary.*Escape"

# Run xfce4-panel in foreground with debug output
xfce4-panel -q && PANEL_DEBUG=1 xfce4-panel
```
