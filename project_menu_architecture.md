# Project Architecture Summary: Menu Identifiers & Key Bindings (`en_US`)

## 1. Current Distribution of Menu & Shortcut Data

In the current codebase, definitions for system menu items, commands, and shortcuts are split across **four separate places**:

| Module / Component | Responsibility | How Identifiers & Bindings Are Stored |
| :--- | :--- | :--- |
| **`sys_winx_menu.py`** (`get_winx_schema`) | Visual structure of the menu: item ordering, submenu nesting, and `gettext` translatable labels `_("...")`. | String action keys (`"terminal"`, `"settings"`, `"halt"`, etc.). |
| **`sys_winx_menu.py`** (`DEFAULT_WINX_KEYS` & `winx_keys.json`) | In-menu quick keys (`Win+X, <key>`) and user overrides in `~/.config/xfce-start-menu/winx_keys.json`. | Dictionary `cmd_key -> key_spec` (e.g. `"installed_apps": "a"`, whereas the Win 11 reference expects `"F"`). |
| **`sys_actions.py`** (`WINX_COMMANDS` & `resolve_action`) | Actual shell commands, Python callables (e.g. `_toggle_show_desktop`), and package names for auto-install prompts. | Dictionary `cmd_key -> (command_or_callable, apt_package)`. |
| **`sys_shortcuts.py`** (`DEFAULT_SHORTCUTS`) | Global XFCE keyboard shortcuts (`xfconf-query` / `xfce4-keyboard-shortcuts`) and tooltip hint generation. | Dictionary `cmd_key -> (accel_str, [xfconf_property_paths])`. |

---

## 2. Main Causes of Desynchronization

1. **Mismatch Between `DEFAULT_WINX_KEYS` and the Windows 11 Reference:**
   * `DEFAULT_WINX_KEYS` currently defines `"installed_apps": "a"`, while the Windows 11 standard uses **`"F"`**.
   * Because `~/.config/xfce-start-menu/winx_keys.json` is generated once on first run, updating defaults in Python code does not update an existing user JSON file on disk.
2. **Duplicate Mapping of Action ↔ Global Shortcut:**
   * Global shortcuts (such as `<Super>i`) are mapped to `cmd_key` inside `DEFAULT_SHORTCUTS`, while the actual XFCE `xfconf` registry (`xfce4-keyboard-shortcuts`) may still bind `<Super>i` to a different binary (e.g. `xfce4-terminal`), requiring manual exclusions in `sys_winx_menu.py` (`if cmd_key not in ("terminal", "terminal_admin"):`).
3. **Lack of a Single Source of Truth:**
   * Adding or modifying a single menu entry requires keeping 3–4 separate dictionaries in sync across multiple modules (`get_winx_schema`, `DEFAULT_WINX_KEYS`, `WINX_COMMANDS`, `DEFAULT_SHORTCUTS`), making typos and key swaps (such as `settings` vs. `search`) easy to introduce.
