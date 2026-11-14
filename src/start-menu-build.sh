#!/bin/sh
echo ""
set -x

gcc -shared -fPIC start-menu.c -o libstartmenu.so \
    $(pkg-config --cflags --libs python3-embed libxfce4panel-2.0 pygobject-3.0) -ldl

[ $? -ne 0 ] && echo "======== BUILD ERROR ========"


[ ! -d /usr/lib/x86_64-linux-gnu/xfce4/panel/plugins/ ] && echo "======== INSTALL ERROR ========"
sudo cp libstartmenu.so /usr/lib/x86_64-linux-gnu/xfce4/panel/plugins/
