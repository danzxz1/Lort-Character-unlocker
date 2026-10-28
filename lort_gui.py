#!/usr/bin/env python3
"""LORT Character Unlocker: графический интерфейс (tkinter, без зависимостей).

Запуск:  python lort_gui.py [--save-dir <папка SaveGames>]
"""
import argparse
import json
import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import extract_portraits  # noqa: E402
import lort_unlocker as core  # noqa: E402

PORTRAITS = os.path.join(HERE, "portraits")

# порядок карточек: ключ, имя, класс, цвет рамки; открытые по умолчанию ключа в core.HEROES не имеют
CARDS = [
    ("warrior", "Astrid Glitzgore", "Warrior", "#c0583a"),
    ("ranger", "Cliff Bowman", "Ranger", "#5fa05a"),
    ("wizard", "Bernie Blazington", "Wizard", "#e58a2e"),
    ("rogue", "Croaks Malone", "Rogue", "#7bb34a"),
    ("monk", "Xavier", "Monk", "#d8504a"),
    ("icemage", "Stacy of Chillendell", "IceMage", "#4fb3e8"),
    ("paladin", "Marcus T. Fury", "Paladin", "#4a8fd8"),
]
COLUMNS = 4

BG, PANEL, TEXT, MUTED = "#15171c", "#1f232b", "#e8eaed", "#8b93a1"
OPEN_COLOR, LOCKED_COLOR, ACCENT = "#4cc275", "#e0605a", "#e7a43a"

# стиль кнопки: (фон, фон при наведении, фон при нажатии, цвет текста, цвет рамки)
BUTTON_STYLES = {
    "unlock": ("#34b866", "#4fd283", "#2a9a55", "#07210f", "#34b866"),
    "lock": ("#2a1d20", "#e0605a", "#c24a45", "#e0605a", "#e0605a"),
    "gold": ("#e7a43a", "#f5bc5c", "#cc8d28", "#1a1304", "#e7a43a"),
    "ghost": (PANEL, "#2d3340", "#1a1d24", TEXT, "#3a4150"),
    "disabled": ("#1a1d24", "#1a1d24", "#1a1d24", "#5d6575", "#262b35"),
}


class RoundButton(tk.Canvas):
    """Скруглённая кнопка с подсветкой при наведении и эффектом нажатия."""

    def __init__(self, parent, text, command, style="ghost", height=40, fixed_width=False):
        super().__init__(parent, height=height, highlightthickness=0, bd=0, bg=parent["bg"], cursor="hand2")
        self.text, self.command, self.style, self.fixed_width = text, command, style, fixed_width
        self.width_texts = None  # все варианты текста (по языкам): ширина по самому длинному, чтобы не прыгала
        self.font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.state = "normal"
        self.hover = self.pressed = False
        if fixed_width:
            self.config(width=10)  # реальную ширину задаёт pack(fill="x")
        self.bind("<Configure>", lambda _e: self._draw())
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self._resize()

    def set(self, text=None, style=None, command=None, enabled=None):
        if text is not None:
            self.text = text
        if style is not None:
            self.style = style
        if command is not None:
            self.command = command
        if enabled is not None:
            self.state = "normal" if enabled else "disabled"
            self.config(cursor="hand2" if enabled else "arrow")
        self._resize()
        self._draw()

    def _resize(self):
        if not self.fixed_width:
            self.config(width=max(self.font.measure(t) for t in (self.width_texts or [self.text])) + 40)

    def _set_hover(self, value):
        self.hover = value and self.state == "normal"
        self._draw()

    def _press(self, _e):
        if self.state == "normal":
            self.pressed = True
            self._draw()

    def _release(self, e):
        was = self.pressed
        self.pressed = False
        self._draw()
        if was and self.state == "normal" and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self.command()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        r = min(18, h // 2 - 2)
        if w < 4:
            return
        bg, hover, pressed, fg, border = BUTTON_STYLES["disabled" if self.state == "disabled" else self.style]
        fill = pressed if self.pressed else hover if self.hover else bg
        if self.style == "lock" and self.hover and self.state == "normal":
            fg = "#ffffff"
        x0, y0, x1, y1 = 2, 2, w - 2, h - 2
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
               x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        self.create_polygon(pts, smooth=True, fill=fill, outline=border, width=2)
        self.create_text(w / 2, h / 2 + (1 if self.pressed else 0), text=self.text, fill=fg, font=self.font)


STRINGS = {
    "en": {
        "profile": "Profile:",
        "folder": "📁  Folder…",
        "lang": "🌐  English",
        "st_default": "● Unlocked from the start",
        "st_open": "● Unlocked",
        "st_locked": "🔒 Locked",
        "btn_unlock": "🔓  Unlock",
        "btn_lock": "🔒  Lock",
        "btn_avail": "✔  Available",
        "btn_all": "✨  Unlock all",
        "btn_restore": "↩  Restore",
        "btn_portraits": "🖼  Load portraits",
        "no_profiles": "No LORT profiles found. Click “Folder…” and pick your SaveGames folder.",
        "read_error": "Could not read the profile: {err}",
        "running_title": "Game is running",
        "running_save": "Close LORT first: the game overwrites the save when it exits.",
        "running_restore": "Close LORT before restoring.",
        "no_change_lock": "Nothing changed: the hero is already locked.",
        "no_change_unlock": "Nothing changed: the hero is already unlocked.",
        "write_error": "Write error",
        "done_unlock": "Unlocked: {names}. Backup: {backup}. Steam Cloud may overwrite the save, wait for the sync to finish.",
        "done_lock": "Locked: {names}. Backup: {backup}. Steam Cloud may overwrite the save, wait for the sync to finish.",
        "lock_title": "Lock hero",
        "lock_body": "Lock {name} again?\nTheir challenge and the weapon it granted will be removed. A backup is created first.",
        "no_backup": "No backups for this profile.",
        "restore_title": "Restore",
        "restore_body": "Restore the profile from {backup}?",
        "restored": "Profile restored from {backup}.",
        "pick_retoc": "Select retoc (github.com/trumank/retoc/releases)",
        "pick_game": "LORT game folder (must contain BW/Content/Paks)",
        "portraits_title": "Portraits",
        "portraits_ok": "Portraits loaded.",
        "pick_saves": "SaveGames folder (or the Steam ID folder)",
    },
    "ru": {
        "profile": "Профиль:",
        "folder": "📁  Папка…",
        "lang": "🌐  Русский",
        "st_default": "● Открыт с начала",
        "st_open": "● Открыт",
        "st_locked": "🔒 Закрыт",
        "btn_unlock": "🔓  Разблокировать",
        "btn_lock": "🔒  Заблокировать",
        "btn_avail": "✔  Доступен",
        "btn_all": "✨  Разблокировать всех",
        "btn_restore": "↩  Откатить",
        "btn_portraits": "🖼  Загрузить портреты",
        "no_profiles": "Профили LORT не найдены. Нажмите «Папка…» и укажите SaveGames.",
        "read_error": "Не удалось прочитать профиль: {err}",
        "running_title": "Игра запущена",
        "running_save": "Закройте LORT: при выходе игра перезапишет сохранение.",
        "running_restore": "Закройте LORT перед откатом.",
        "no_change_lock": "Изменений нет: герой уже закрыт.",
        "no_change_unlock": "Изменений нет: герой уже открыт.",
        "write_error": "Ошибка записи",
        "done_unlock": "Открыто: {names}. Бэкап: {backup}. Steam Cloud может подменить сохранение, дождитесь синхронизации.",
        "done_lock": "Заблокировано: {names}. Бэкап: {backup}. Steam Cloud может подменить сохранение, дождитесь синхронизации.",
        "lock_title": "Заблокировать героя",
        "lock_body": "Снова закрыть героя {name}?\nБудет убран его челлендж и выданное оружие. Перед этим создаётся бэкап.",
        "no_backup": "Бэкапов для этого профиля нет.",
        "restore_title": "Откат",
        "restore_body": "Вернуть профиль из {backup}?",
        "restored": "Профиль восстановлен из {backup}.",
        "pick_retoc": "Укажите retoc (github.com/trumank/retoc/releases)",
        "pick_game": "Папка игры LORT (внутри должна быть BW/Content/Paks)",
        "portraits_title": "Портреты",
        "portraits_ok": "Портреты загружены.",
        "pick_saves": "Папка SaveGames (или папка со Steam ID)",
    },
}
DEFAULT_LANG = "en"
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".lort_unlocker.json")


def load_lang():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            lang = json.load(f).get("lang")
        return lang if lang in STRINGS else DEFAULT_LANG
    except (OSError, ValueError, AttributeError):
        return DEFAULT_LANG


def save_lang(lang):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f)
    except OSError:
        pass  # язык просто не запомнится


class App(tk.Tk):
    def __init__(self, save_dir, lang):
        super().__init__()
        self.title("LORT Character Unlocker")
        self.configure(bg=BG)
        self.minsize(900, 640)
        self.save_dir = save_dir
        self.lang = lang
        self.last_message = None  # (ключ, цвет, параметры): пересобирается при смене языка
        self.profiles = []
        self.images = {}
        self.cards = {}
        self.data = None
        self._style()
        self._build_header()
        self.grid_frame = tk.Frame(self, bg=BG)
        self.grid_frame.pack(padx=20, pady=(0, 8))
        self._build_cards()
        self._build_footer()
        self.apply_language()
        self.reload_profiles()

    def t(self, key, **kw):
        return STRINGS[self.lang][key].format(**kw)

    # ---------- оформление ----------
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=TEXT,
                    arrowcolor=TEXT, bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL)
        s.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", TEXT)])
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)

    def _button(self, parent, text, command, style="ghost", text_key=None, **kwargs):
        btn = RoundButton(parent, text, command, style=style, **kwargs)
        if text_key:
            btn.width_texts = [STRINGS[lang][text_key] for lang in STRINGS]
        return btn

    def _build_header(self):
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=20, pady=(16, 10))
        tk.Label(head, text="LORT Character Unlocker", bg=BG, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        right = tk.Frame(head, bg=BG)
        right.pack(side="right")
        self.lang_btn = self._button(right, "", self.toggle_language, height=34, text_key="lang")
        self.lang_btn.pack(side="right", padx=(8, 0))
        self.folder_btn = self._button(right, "", self.choose_dir, height=34, text_key="folder")
        self.folder_btn.pack(side="right", padx=(8, 0))
        self.profile_var = tk.StringVar()
        self.profile_box = ttk.Combobox(right, textvariable=self.profile_var, state="readonly", width=34)
        self.profile_box.pack(side="right")
        self.profile_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self.profile_label = tk.Label(right, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10), width=10, anchor="e")
        self.profile_label.pack(side="right", padx=(0, 6))

    def _build_cards(self):
        for i, (key, name, cls, color) in enumerate(CARDS):
            frame = tk.Frame(self.grid_frame, bg=PANEL, highlightthickness=2, highlightbackground=PANEL)
            frame.grid(row=i // COLUMNS, column=i % COLUMNS, padx=8, pady=8, sticky="n")
            canvas = tk.Canvas(frame, width=192, height=192, bg=PANEL, highlightthickness=0)
            canvas.pack(padx=10, pady=(10, 8))
            tk.Label(frame, text=name, bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack()
            tk.Label(frame, text=cls, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack()
            status = tk.Label(frame, text="", bg=PANEL, font=("Segoe UI", 10, "bold"), width=26)
            status.pack(pady=(6, 6))
            btn = self._button(frame, "", lambda k=key: self.unlock_one(k), style="unlock",
                               height=42, fixed_width=True)
            btn.pack(fill="x", padx=10, pady=(0, 12))
            self.cards[key] = dict(frame=frame, canvas=canvas, status=status, button=btn, color=color,
                                   name=name, cls=cls)

    def _build_footer(self):
        foot = tk.Frame(self, bg=BG)
        foot.pack(fill="x", padx=20, pady=(4, 16))
        self.message = tk.Label(foot, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="nw",
                                justify="left", wraplength=400, height=3, width=1)
        self.message.pack(side="left", fill="x", expand=True)
        self.restore_btn = self._button(foot, "", self.restore, height=44, text_key="btn_restore")
        self.restore_btn.pack(side="right", padx=(8, 0))
        self.all_btn = self._button(foot, "", self.unlock_all, style="gold", height=44, text_key="btn_all")
        self.all_btn.pack(side="right")
        self.portrait_btn = self._button(foot, "", self.load_portraits, height=44, text_key="btn_portraits")

    # ---------- язык ----------
    def apply_language(self):
        self.profile_label.config(text=self.t("profile"))
        self.folder_btn.set(text=self.t("folder"))
        self.lang_btn.set(text=self.t("lang"))
        self.all_btn.set(text=self.t("btn_all"))
        self.restore_btn.set(text=self.t("btn_restore"))
        self.portrait_btn.set(text=self.t("btn_portraits"))
        if self.profiles or self.data is not None:
            self.refresh()
        if self.last_message:
            key, color, kw = self.last_message
            self.say(key, color, **kw)

    def toggle_language(self):
        self.lang = "ru" if self.lang == "en" else "en"
        save_lang(self.lang)
        self.apply_language()

    # ---------- портреты ----------
    def portrait(self, key, locked):
        suffix = "_locked" if locked else ""
        cache_key = key + suffix
        if cache_key not in self.images:
            path = os.path.join(PORTRAITS, cache_key + ".png")
            try:
                self.images[cache_key] = tk.PhotoImage(file=path) if os.path.isfile(path) else None
            except tk.TclError:
                self.images[cache_key] = None
        return self.images[cache_key]

    def draw_portrait(self, key, locked):
        card = self.cards[key]
        canvas = card["canvas"]
        canvas.delete("all")
        img = self.portrait(key, locked)
        if img:
            canvas.create_image(96, 96, image=img)
        else:
            canvas.create_rectangle(0, 0, 192, 192, fill="#2a2f3a", outline="")
            canvas.create_text(96, 96, text=card["cls"][0], fill="#555d6d" if locked else card["color"],
                               font=("Segoe UI", 72, "bold"))
        if locked:
            canvas.create_text(172, 20, text="🔒", font=("Segoe UI Emoji", 16), fill=TEXT)

    def load_portraits(self):
        retoc = shutil.which("retoc") or filedialog.askopenfilename(title=self.t("pick_retoc"))
        if not retoc:
            return
        game = extract_portraits.find_game_dir()
        if not game:
            game = filedialog.askdirectory(title=self.t("pick_game"))
        if not game:
            return
        try:
            extract_portraits.extract(retoc, game, log=lambda _m: None)
        except Exception as e:  # noqa: BLE001 - показываем пользователю любую ошибку извлечения
            messagebox.showerror(self.t("portraits_title"), str(e))
            return
        self.images.clear()
        self.refresh()
        self.say("portraits_ok", OPEN_COLOR)

    # ---------- данные ----------
    def reload_profiles(self):
        roots = [self.save_dir] if self.save_dir else core.find_save_roots()
        self.profiles = [p for r in roots for p in core.find_profiles(r)]
        self.profile_box["values"] = self.profiles
        if self.profiles:
            # по умолчанию - первый профиль, в котором уже есть прогресс
            def has_progress(p):
                try:
                    return bool(core.load(p)[0].get("completedChallenges"))
                except (OSError, ValueError):
                    return False
            self.profile_var.set(next((p for p in self.profiles if has_progress(p)), self.profiles[0]))
        else:
            self.profile_var.set("")
        self.refresh()

    def choose_dir(self):
        d = filedialog.askdirectory(title=self.t("pick_saves"))
        if d:
            self.save_dir = d
            self.reload_profiles()

    def current(self):
        path = self.profile_var.get()
        if not path or not os.path.isfile(path):
            return None
        return path

    def refresh(self):
        path = self.current()
        self.data = None
        if path:
            try:
                self.data, self.crlf = core.load(path)
            except (OSError, ValueError) as e:
                self.say("read_error", LOCKED_COLOR, err=e)
        any_locked = False
        for key, card in self.cards.items():
            if key not in core.HEROES:
                state, text, color = "default", self.t("st_default"), OPEN_COLOR
            elif self.data is not None and core.is_open(self.data, key):
                state, text, color = "open", self.t("st_open"), OPEN_COLOR
            else:
                state, text, color = "locked", self.t("st_locked"), LOCKED_COLOR
            locked = state == "locked"
            any_locked |= locked and self.data is not None
            card["status"].config(text=text, fg=color)
            card["frame"].config(highlightbackground=PANEL if locked else card["color"])
            can_unlock = locked and self.data is not None
            can_lock = state == "open"
            if can_unlock:
                card["button"].set(text=self.t("btn_unlock"), style="unlock", enabled=True,
                                   command=lambda k=key: self.unlock_one(k))
            elif can_lock:
                card["button"].set(text=self.t("btn_lock"), style="lock", enabled=True,
                                   command=lambda k=key: self.lock_one(k))
            else:
                card["button"].set(text=self.t("btn_avail"), enabled=False)
            self.draw_portrait(key, locked)
        self.all_btn.set(enabled=any_locked)
        missing = not all(os.path.isfile(os.path.join(PORTRAITS, k + ".png")) for k in self.cards)
        if missing:
            self.portrait_btn.pack(side="right", padx=(0, 8))
        else:
            self.portrait_btn.pack_forget()
        if not self.profiles:
            self.say("no_profiles", ACCENT)

    # ---------- действия ----------
    def say(self, key, color=MUTED, **kw):
        self.last_message = (key, color, kw)
        self.message.config(text=self.t(key, **kw), fg=color)

    def apply(self, keys, locking=False):
        path = self.current()
        if not path or self.data is None:
            return
        if core.game_running():
            messagebox.showwarning(self.t("running_title"), self.t("running_save"))
            return
        data, crlf = core.load(path)
        action = core.lock if locking else core.unlock
        changed = [k for k in keys if action(data, k)]
        if not changed:
            self.say("no_change_lock" if locking else "no_change_unlock")
            return
        try:
            backup = core.make_backup(path)
            core.save(path, data, crlf)
        except OSError as e:
            messagebox.showerror(self.t("write_error"), str(e))
            return
        self.refresh()
        self.say("done_lock" if locking else "done_unlock", ACCENT if locking else OPEN_COLOR,
                 names=", ".join(self.cards[k]["name"] for k in changed), backup=os.path.basename(backup))

    def unlock_one(self, key):
        if key in core.HEROES:
            self.apply([key])

    def lock_one(self, key):
        if key in core.HEROES and messagebox.askyesno(
                self.t("lock_title"), self.t("lock_body", name=self.cards[key]["name"])):
            self.apply([key], locking=True)

    def unlock_all(self):
        self.apply(list(core.HEROES))

    def restore(self):
        path = self.current()
        backup = path and core.latest_backup(path)
        if not backup:
            self.say("no_backup", ACCENT)
            return
        if core.game_running():
            messagebox.showwarning(self.t("running_title"), self.t("running_restore"))
            return
        name = os.path.basename(backup)
        if messagebox.askyesno(self.t("restore_title"), self.t("restore_body", backup=name)):
            shutil.copy2(backup, path)
            self.refresh()
            self.say("restored", OPEN_COLOR, backup=name)


def main():
    ap = argparse.ArgumentParser(description="LORT Character Unlocker (GUI)")
    ap.add_argument("-s", "--save-dir", help="SaveGames folder (auto-detected by default)")
    ap.add_argument("--lang", choices=list(STRINGS), help="interface language (default: English, or the last choice)")
    args = ap.parse_args()
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    App(args.save_dir, args.lang or load_lang()).mainloop()


if __name__ == "__main__":
    sys.exit(main())
