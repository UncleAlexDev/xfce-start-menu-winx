DOMAIN = xfce-start-menu
LOCALE_DIR = locale
POT_FILE = $(LOCALE_DIR)/$(DOMAIN).pot
LANGS = ru

VERSION := $(strip $(shell cat VERSION 2>/dev/null || echo "0.0.0"))

# System installation paths (override with PREFIX=/usr/local if needed)
PREFIX ?= /usr
PLUGIN_DIR ?= $(PREFIX)/share/xfce-start-menu
DATADIR ?= $(PREFIX)/share/xfce4/panel/plugins
LOCALEDIR_SYS ?= $(PREFIX)/share/locale

# Detect distribution and architecture for LIBDIR
ARCH := $(shell uname -m)
OS_RELEASE := $(shell [ -f /etc/os-release ] && grep -E '^(ID|ID_LIKE)=' /etc/os-release || true)

ifneq ($(findstring debian,$(OS_RELEASE))$(findstring ubuntu,$(OS_RELEASE)),)
    # Debian, Ubuntu, Linux Mint, Pop!_OS, Kali, etc.
    LIBDIR ?= $(PREFIX)/lib/$(ARCH)-linux-gnu/xfce4/panel/plugins
else ifneq ($(findstring fedora,$(OS_RELEASE))$(findstring rhel,$(OS_RELEASE))$(findstring suse,$(OS_RELEASE)),)
    # Fedora, RHEL, CentOS, Alma, Rocky, openSUSE (64-bit uses lib64)
    ifeq ($(ARCH),x86_64)
        LIBDIR ?= $(PREFIX)/lib64/xfce4/panel/plugins
    else ifeq ($(ARCH),aarch64)
        LIBDIR ?= $(PREFIX)/lib64/xfce4/panel/plugins
    else
        LIBDIR ?= $(PREFIX)/lib/xfce4/panel/plugins
    endif
else
    # Arch, Manjaro, EndeavourOS, Gentoo, Alpine, Void, etc.
    LIBDIR ?= $(PREFIX)/lib/xfce4/panel/plugins
endif

# C Plugin settings & Python shared library detection
CC = gcc
PLUGIN_SRC = start-menu.c
PLUGIN_LIB = libstartmenu.so
PY_VER := $(shell python3 -c "import sysconfig; print(sysconfig.get_config_var('LDLIBRARY'))")
PKGS = libxfce4panel-2.0 gtk+-3.0 python3-embed pygobject-3.0

CFLAGS = -Wall -O2 -fPIC \
         -DPY_LIB_NAME=\"$(PY_VER)\" \
         -DPLUGIN_DIR=\"$(PLUGIN_DIR)\" \
         $(shell pkg-config --cflags $(PKGS))
LDFLAGS = -shared $(shell pkg-config --libs $(PKGS))

# Localization & Desktop files
PY_FILES = start-menu-sys.py start-menu-app.py
DESKTOP_IN = start-menu.desktop.in
DESKTOP_OUT = start-menu.desktop

.PHONY: all plugin pot po mo desktop install uninstall clean

# Default target: build C library, translations, and .desktop file
all: plugin pot po mo desktop

# 1. Compile the C wrapper library for xfce4-panel
plugin: $(PLUGIN_LIB)

$(PLUGIN_LIB): $(PLUGIN_SRC)
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)
	@echo "Built $(PLUGIN_LIB)"

# 2. Extract translatable strings from Python and .desktop.in
pot: $(PY_FILES) $(DESKTOP_IN)
	@mkdir -p $(LOCALE_DIR)
	#@echo "$(LANGS)" > $(LOCALE_DIR)/LINGUAS
	xgettext --language=Python --keyword=_ --from-code=UTF-8 \
		--package-name=$(DOMAIN) \
		--output=$(POT_FILE) $(PY_FILES)
	xgettext --language=Desktop --join-existing --from-code=UTF-8 \
		--output=$(POT_FILE) $(DESKTOP_IN)
	@echo "Updated template $(POT_FILE)"

# 3. Initialize or update .po files without losing existing translations
po: pot
	@for lang in $(LANGS); do \
		po_file="$(LOCALE_DIR)/$$lang/LC_MESSAGES/$(DOMAIN).po"; \
		mkdir -p "$$(dirname $$po_file)"; \
		if [ -f "$$po_file" ]; then \
			msgmerge --update --backup=none "$$po_file" $(POT_FILE); \
			echo "Updated $$po_file"; \
		else \
			msginit --no-translator --input=$(POT_FILE) --locale=$$lang.UTF-8 --output="$$po_file"; \
			echo "Created $$po_file"; \
		fi; \
	done

# 4. Compile .po files into binary .mo files
mo:
	@for lang in $(LANGS); do \
		po_file="$(LOCALE_DIR)/$$lang/LC_MESSAGES/$(DOMAIN).po"; \
		mo_file="$(LOCALE_DIR)/$$lang/LC_MESSAGES/$(DOMAIN).mo"; \
		if [ -f "$$po_file" ]; then \
			msgfmt "$$po_file" -o "$$mo_file"; \
			echo "Compiled $$mo_file"; \
		fi; \
	done

# 5. Merge translations back into the final .desktop file
desktop: mo $(DESKTOP_IN) VERSION
	@tmpdir=$$(mktemp -d); \
	echo "$(LANGS)" > "$$tmpdir/LINGUAS"; \
	for lang in $(LANGS); do \
		ln -s "$(CURDIR)/$(LOCALE_DIR)/$$lang/LC_MESSAGES/$(DOMAIN).po" "$$tmpdir/$$lang.po"; \
	done; \
	msgfmt --desktop --template=$(DESKTOP_IN) -d "$$tmpdir" -o $(DESKTOP_OUT); \
	rm -rf "$$tmpdir"
	sed -i -E 's/^(Name(\[[^]]+\])?=.*)$$/\1  Ver. $(VERSION)/' $(DESKTOP_OUT)
	@echo "Generated $(DESKTOP_OUT) (v$(VERSION))"


# 6. Install plugin, scripts, desktop file, and compiled locales to the system
install: all
	install -Dm755 $(PLUGIN_LIB) $(DESTDIR)$(LIBDIR)/$(PLUGIN_LIB)
	install -Dm644 $(DESKTOP_OUT) $(DESTDIR)$(DATADIR)/$(DESKTOP_OUT)
	install -Dm644 start-menu-sys.py $(DESTDIR)$(PLUGIN_DIR)/start-menu-sys.py
	install -Dm755 start-menu-app.py $(DESTDIR)$(PLUGIN_DIR)/start-menu-app.py
	install -Dm644 VERSION $(DESTDIR)$(PLUGIN_DIR)/VERSION
	@for lang in $(LANGS); do \
		mo_file="$(LOCALE_DIR)/$$lang/LC_MESSAGES/$(DOMAIN).mo"; \
		if [ -f "$$mo_file" ]; then \
			install -v -Dm644 "$$mo_file" "$(DESTDIR)$(LOCALEDIR_SYS)/$$lang/LC_MESSAGES/$(DOMAIN).mo"; \
		fi; \
	done
	@echo ""
	@ls -la $(DESTDIR)$(LIBDIR)/$(PLUGIN_LIB) \
			$(DESTDIR)$(DATADIR)/$(DESKTOP_OUT) \
			$(DESTDIR)$(PLUGIN_DIR)/start-menu-sys.py \
			$(DESTDIR)$(PLUGIN_DIR)/start-menu-app.py
	@for lang in $(LANGS); do \
	    ls -la "$(DESTDIR)$(LOCALEDIR_SYS)/$$lang/LC_MESSAGES/$(DOMAIN).mo" ; \
	done
	@echo "Installation complete."
	@echo ""
	@echo "Restart xfce4-panel with: xfce4-panel -r"
	@echo ""

# 7. Remove installed files from the system
uninstall:
	rm -f $(DESTDIR)$(LIBDIR)/$(PLUGIN_LIB)
	rm -f $(DESTDIR)$(DATADIR)/$(DESKTOP_OUT)
	rm -rf $(DESTDIR)$(PLUGIN_DIR)
	@for lang in $(LANGS); do \
		rm -f "$(DESTDIR)$(LOCALEDIR_SYS)/$$lang/LC_MESSAGES/$(DOMAIN).mo"; \
	done
	@echo "Uninstallation complete."

# Clean generated build artifacts (keeps .po files intact)
clean:
	rm -f $(PLUGIN_LIB) $(POT_FILE) $(DESKTOP_OUT) $(LOCALE_DIR)/LINGUAS $(LOCALE_DIR)/*/LC_MESSAGES/*.mo
	@echo "Cleaned build artifacts."
