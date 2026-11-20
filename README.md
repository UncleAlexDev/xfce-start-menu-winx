# Xfce Start Menu

Start menu button for Xfce.
The best of the Windows 11 Start button, applied to XFCE.
On Phyton on Glib.

## The first MVP
Currently just Minimum Viable Product.


## How to build

```
$ make plugin
$ make pot
$ make po
$ make mo
$ make desktop
```
or 
```
$ make plugin pot po mo desktop
```
or
```
$ make all
```

## How to install

```
sudo make install
```
as result:
```
-rwxr-xr-x 1 root root 17104 ноя 15 19:28 /usr/lib/x86_64-linux-gnu/xfce4/panel/plugins/libstartmenu.so
-rw-r--r-- 1 root root   338 ноя 15 19:28 /usr/share/xfce4/panel/plugins/start-menu.desktop
-rwxr-xr-x 1 root root 19917 ноя 15 19:28 /usr/share/xfce-start-menu/start-menu-app.py
-rw-r--r-- 1 root root  7683 ноя 15 19:28 /usr/share/xfce-start-menu/start-menu-sys.py
-rw-r--r-- 1 root root  1491 ноя 15 19:28 /usr/share/locale/ru/LC_MESSAGES/xfce-start-menu.mo
```

## Setup shortkeys

- Get plugin number on xfce panel:
```
$ xfconf-query -c xfce4-panel -p /plugins -l -v | grep start-menu
/plugins/plugin-14  start-menu
```

- Keyboard settings

Go to Settings -> Keyboard -> Keys -> Add 
```
xfce4-panel --plugin-event=start-menu-14:start:bool:true   Win
```
```
xfce4-panel --plugin-event=start-menu-14:winx:bool:true    Win+X
```


### Misc (under develop)

The list of suitable command for administration and debug
```
xfconf-query -c xfce4-panel -p /plugins -l -v | grep start-menu
xfce4-panel -q && PANEL_DEBUG=1 xfce4-panel
```
