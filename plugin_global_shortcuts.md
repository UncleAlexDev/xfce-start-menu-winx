# XFCE Start Menu — Global Shortcuts Reference (`xfce4-keyboard-shortcuts`)

This table defines the canonical global shortcuts registered in `xfconf` (`xfce4-keyboard-shortcuts` channel) for the `start-menu` panel plugin.

| Action Key (`cmd_key`) | `xfconf` Shortcut (`/commands/custom/...`) | Target Command | Cleanup Paths (Conflicts to Remove) |
| :--- | :--- | :--- | :--- |
| **`start`** | `Super_L` | `xfce4-panel --plugin-event=start-menu:start:bool:true` | `/commands/default/Super_L` |
| **`winx`** | `<Super>x` | `xfce4-panel --plugin-event=start-menu:winx:bool:true` | `/commands/default/<Super>x` |
| **`settings`** | `<Super>i` | `xfce4-panel --plugin-event=start-menu:settings:bool:true` | `/commands/default/<Super>i` |
| **`file_explorer`** | `<Super>e` | `xfce4-panel --plugin-event=start-menu:file_explorer:bool:true` | `/commands/default/<Super>e` |
| **`search`** | `<Super>s` | `xfce4-panel --plugin-event=start-menu:search:bool:true` | `/commands/default/<Super>s` |
| **`run`** | `<Super>r` | `xfce4-panel --plugin-event=start-menu:run:bool:true` | `/commands/default/<Super>r` |
| **`task_manager`** | `<Primary><Shift>Escape` | `xfce4-panel --plugin-event=start-menu:task_manager:bool:true` | `/commands/default/<Primary><Shift>Escape` |
| **`desktop`** | `<Super>d` | `xfce4-panel --plugin-event=start-menu:desktop:bool:true` | `/commands/default/<Super>d`, `/xfwm4/custom/<Super>d` |

## Notes

* **Single Event Bus**: All global shortcuts route through `xfce4-panel --plugin-event=start-menu:<cmd_key>:bool:true`, allowing the plugin to handle positioning, focus, and internal logic (such as the custom `Run` dialog) uniformly.
* **Conflict Resolution**: Default entries under `/commands/default/...` and window manager overrides under `/xfwm4/custom/<Super>d` must be removed to prevent duplicate entries in XFCE Keyboard Settings or double triggers.
