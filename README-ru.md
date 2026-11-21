# Xfce Start Menu

Современная кнопка «Пуск» и системное меню быстрого доступа в стиле **Windows 11 (`Win+X`)** для панели **Xfce4**, написанные на **Python 3**, **GTK 3 / GLib** с лёгкой C-обёрткой для `libxfce4panel`.

> **Статус:** Рабочий MVP (минимально жизнеспособный продукт)

---

## Возможности и особенности

* **Два режима работы кнопки на панели:**
  * **ЛКМ (`Win`)** — открывает главное меню приложений (`start-menu-app.py` через D-Bus или прямым запуском).
  * **ПКМ (`Win+X`)** — открывает системное меню опытного пользователя (`sys_winx_menu.py`) по образцу Windows 11 (терминалы, диспетчер задач, параметры, управление питанием и др.).
  * **Shift + ПКМ** — открывает стандартные свойства элемента панели Xfce.
* **Навигация клавишами внутри меню `Win+X` независимо от раскладки:**
  * Поддержка быстрых клавиш при открытом меню (например, `Win+X, I` — Терминал, `Win+X, A` — Терминал (Администратор), `Win+X, U → R` — Перезагрузка).
  * Срабатывает вне зависимости от текущей раскладки (латиница, кириллица) и состояния `CapsLock`/`Shift` через `Gdk.Keymap`.
  * Карта клавиш вынесена в пользовательский конфиг `~/.config/xfce-start-menu/winx_keys.json` (создаётся автоматически при первом запуске).
* **Автоматическая синхронизация и проверка глобальных хоткеев (`xfconf`):**
  * Плагин сам проверяет и привязывает глобальные комбинации (`Win`, `Win+X`, `Win+I`, `Win+S`, `Win+E`, `Win+R`, `Win+D`, `Ctrl+Shift+Esc`) в канале `xfce4-keyboard-shortcuts`.
  * При обнаружении конфликтов или отсутствующих хоткеев выводит диалог с предложением исправить их автоматически, открыть **Настройки клавиатуры Xfce** или оставить как есть.
* **Собственный диалог «Выполнить» (`Win+R`):**
  * Встроенное окно `Run` (`sys_cmd.py`), позиционируемое строго у края панели (сверху, снизу, слева или справа).
  * Автодополнение исполняемых файлов из `$PATH` по клавише `Tab`, сохранение истории команд (`~/.cache/xfce-start-menu/run_history.json`) и виртуальная команда `cmd` для запуска системного терминала Xfce.
* **Отложенные подсказки и установка недостающих утилит:**
  * Нативные тултипы GTK появляются через 3 секунды наведения и показывают как глобальный хоткей, так и последовательность в меню (`Win+E  |  Win+X, E`).
  * Отсутствующие необязательные утилиты (например, `gnome-disks`, `hardinfo2`) помечаются индикатором `[!]` и предлагают установку через `apt` в окне терминала.
* **Локализация (`gettext`):**
  * Полный цикл сборки переводов (`pot` / `po` / `mo` + локализация `.desktop`) с поддержкой русского (`ru_RU`) и английского (`en_US`) языков.

---

## Архитектура проекта

| Файл / модуль | Назначение |
| :--- | :--- |
| `src/start-menu.c` | Лёгкая C-библиотека (`libstartmenu.so`), встраивающая интерпретатор Python 3 в `xfce4-panel`. |
| `src/start-menu-sys.py` | Точка входа плагина панели, расчёт координат (anchor), вызов главного меню по D-Bus и маршрутизация `remote-event`. |
| `src/start-menu-app.py` | Главное окно меню «Пуск» / Приложения (`org.custom.xfce.startmenu`). |
| `src/sys_winx_menu.py` | Построитель меню `Win+X`, загрузка `winx_keys.json`, перехват клавиш независимо от раскладки и отложенные тултипы. |
| `src/sys_shortcuts.py` | Единый реестр глобальных хоткеев, проверка расхождений в `xfconf` и интерактивное исправление. |
| `src/sys_actions.py` | Резолвер команд, передача метки времени запуска (`DESKTOP_STARTUP_ID`) и помощник установки пакетов через `apt`. |
| `src/sys_cmd.py` | Диалог «Выполнить» (`Win+R`) с автодополнением из `$PATH` и историей. |
| `src/sys_i18n.py` | Инициализация `gettext` и чтение версии из файла `VERSION`. |

---

## Зависимости для сборки и работы

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

## Сборка и установка

`Makefile` автоматически определяет дистрибутив и архитектуру процессора (`x86_64`, `aarch64` и др.) и выбирает нужный каталог библиотек плагинов панели (`/usr/lib/<arch>-linux-gnu/xfce4/panel/plugins` для Debian/Ubuntu, `/usr/lib64/xfce4/panel/plugins` для Fedora/SUSE, `/usr/lib/xfce4/panel/plugins` для Arch).

1. **Собрать C-библиотеку, обновить переводы и сгенерировать `.desktop` файл:**
   ```bash
   make all
   ```
   *(Отдельные цели: `make plugin`, `make pot`, `make po`, `make mo`, `make desktop`)*

2. **Установить в систему:**
   ```bash
   sudo make install
   ```

3. **Перезапустить панель Xfce и добавить плагин:**
   ```bash
   xfce4-panel -r
   ```
   Нажмите ПКМ по панели Xfce → **Панель → Добавить новые элементы...** → выберите **Start Menu** и разместите кнопку в нужном углу экрана.

4. **Удаление из системы:**
   ```bash
   sudo make uninstall
   ```

---

## Настройка

### 1. Глобальные горячие клавиши (`xfce4-keyboard-shortcuts`)
При запуске панели или открытии меню `Win+X` плагин автоматически сверяет настройки клавиатуры Xfce с эталоном и предлагает прописать стандартные комбинации:

| Действие | Глобальный хоткей | Команда события панели |
| :--- | :--- | :--- |
| Меню приложений («Пуск») | `Win` (`Super_L`) | `xfce4-panel --plugin-event=start-menu:start:bool:true` |
| Системное меню (`Win+X`) | `Win + X` | `xfce4-panel --plugin-event=start-menu:winx:bool:true` |
| Параметры (Settings) | `Win + I` | `xfce4-panel --plugin-event=start-menu:settings:bool:true` |
| Проводник (File Explorer) | `Win + E` | `xfce4-panel --plugin-event=start-menu:file_explorer:bool:true` |
| Поиск (Search) | `Win + S` | `xfce4-panel --plugin-event=start-menu:search:bool:true` |
| Выполнить (Run) | `Win + R` | `xfce4-panel --plugin-event=start-menu:run:bool:true` |
| Диспетчер задач | `Ctrl + Shift + Esc` | `xfce4-panel --plugin-event=start-menu:task_manager:bool:true` |
| Показать рабочий стол | `Win + D` | `xfce4-panel --plugin-event=start-menu:desktop:bool:true` |

> **Примечание:** Если на панели добавлено несколько экземпляров плагина, узнать точный идентификатор можно командой `xfconf-query -c xfce4-panel -p /plugins -l -v | grep start-menu` (например, `start-menu-14`).

### 2. Настройка клавиш внутри меню `Win+X`
При первом открытии системного меню создаётся файл `~/.config/xfce-start-menu/winx_keys.json` со стандартными клавишами Windows 11 (`F`, `O`, `V`, `Y`, `M`, `W`, `K`, `G`, `I`, `A`, `T`, `N`, `E`, `S`, `R`, `U`, `D`). При необходимости любую букву можно переопределить в этом JSON-файле без правки исходного кода.

---

## Отладка и диагностика

```bash
# Узнать номер/идентификатор плагина на панели
xfconf-query -c xfce4-panel -p /plugins -l -v | grep start-menu

# Проверить зарегистрированные хоткеи Super / Esc в xfconf
xfconf-query -c xfce4-keyboard-shortcuts -l -v | grep -iE "super|Primary.*Escape"

# Запустить панель в режиме отладки с выводом логов в терминал
xfce4-panel -q && PANEL_DEBUG=1 xfce4-panel
```

## Author & Support

* **Contract work & custom features:** Contact via `avl.mail.post@gmail.com` (available via [Mellow.io](https://mellow.io))

