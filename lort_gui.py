#!/usr/bin/env python3
"""LORT Character Unlocker: графический интерфейс (tkinter, без зависимостей).

Запуск:  python lort_gui.py [--save-dir <папка SaveGames>]
"""
import argparse
import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

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


class App(tk.Tk):
    def __init__(self, save_dir):
        super().__init__()
        self.title("LORT Character Unlocker")
        self.configure(bg=BG)
        self.minsize(900, 640)
        self.save_dir = save_dir
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
        self.reload_profiles()

    # ---------- оформление ----------
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL, foreground=TEXT,
                    arrowcolor=TEXT, bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL)
        s.map("TCombobox", fieldbackground=[("readonly", PANEL)], foreground=[("readonly", TEXT)])
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)

    def _button(self, parent, text, command, accent=False):
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0, cursor="hand2",
                         bg=ACCENT if accent else PANEL, fg="#1a1304" if accent else TEXT,
                         activebackground="#f2b955" if accent else "#2b303a",
                         activeforeground="#1a1304" if accent else TEXT,
                         disabledforeground=MUTED, font=("Segoe UI", 10, "bold"), padx=14, pady=7)

    def _build_header(self):
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=20, pady=(16, 10))
        tk.Label(head, text="LORT Character Unlocker", bg=BG, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        right = tk.Frame(head, bg=BG)
        right.pack(side="right")
        tk.Label(right, text="Профиль:", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))
        self.profile_var = tk.StringVar()
        self.profile_box = ttk.Combobox(right, textvariable=self.profile_var, state="readonly", width=34)
        self.profile_box.pack(side="left")
        self.profile_box.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        self._button(right, "Папка…", self.choose_dir).pack(side="left", padx=(8, 0))

    def _build_cards(self):
        for i, (key, name, cls, color) in enumerate(CARDS):
            frame = tk.Frame(self.grid_frame, bg=PANEL, highlightthickness=2, highlightbackground=PANEL)
            frame.grid(row=i // COLUMNS, column=i % COLUMNS, padx=8, pady=8, sticky="n")
            canvas = tk.Canvas(frame, width=192, height=192, bg=PANEL, highlightthickness=0)
            canvas.pack(padx=10, pady=(10, 8))
            tk.Label(frame, text=name, bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack()
            tk.Label(frame, text=cls, bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack()
            status = tk.Label(frame, text="", bg=PANEL, font=("Segoe UI", 10, "bold"))
            status.pack(pady=(6, 6))
            btn = self._button(frame, "Разблокировать", lambda k=key: self.unlock_one(k), accent=True)
            btn.pack(fill="x", padx=10, pady=(0, 12))
            self.cards[key] = dict(frame=frame, canvas=canvas, status=status, button=btn, color=color,
                                   name=name, cls=cls)

    def _build_footer(self):
        foot = tk.Frame(self, bg=BG)
        foot.pack(fill="x", padx=20, pady=(4, 16))
        self.message = tk.Label(foot, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w",
                                justify="left", wraplength=560)
        self.message.pack(side="left", fill="x", expand=True)
        self._button(foot, "Откатить", self.restore).pack(side="right", padx=(8, 0))
        self.all_btn = self._button(foot, "Разблокировать всех", self.unlock_all, accent=True)
        self.all_btn.pack(side="right")
        self.portrait_btn = self._button(foot, "Загрузить портреты", self.load_portraits)

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
        retoc = shutil.which("retoc") or filedialog.askopenfilename(
            title="Укажите retoc (github.com/trumank/retoc/releases)")
        if not retoc:
            return
        game = extract_portraits.find_game_dir()
        if not game:
            game = filedialog.askdirectory(title="Папка игры LORT (внутри должна быть BW/Content/Paks)")
        if not game:
            return
        try:
            extract_portraits.extract(retoc, game, log=lambda _m: None)
        except Exception as e:  # noqa: BLE001 - показываем пользователю любую ошибку извлечения
            messagebox.showerror("Портреты", str(e))
            return
        self.images.clear()
        self.refresh()
        self.say("Портреты загружены.", OPEN_COLOR)

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
        d = filedialog.askdirectory(title="Папка SaveGames (или папка со Steam ID)")
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
                self.say("Не удалось прочитать профиль: %s" % e, LOCKED_COLOR)
        any_locked = False
        for key, card in self.cards.items():
            if key not in core.HEROES:
                state, text, color = "default", "● Открыт с начала", OPEN_COLOR
            elif self.data is not None and core.is_open(self.data, key):
                state, text, color = "open", "● Открыт", OPEN_COLOR
            else:
                state, text, color = "locked", "🔒 Закрыт", LOCKED_COLOR
            locked = state == "locked"
            any_locked |= locked and self.data is not None
            card["status"].config(text=text, fg=color)
            card["frame"].config(highlightbackground=PANEL if locked else card["color"])
            can_unlock = locked and self.data is not None
            can_lock = state == "open"
            if can_unlock:
                card["button"].config(state="normal", text="Разблокировать", cursor="hand2", bg=ACCENT, fg="#1a1304",
                                      command=lambda k=key: self.unlock_one(k))
            elif can_lock:
                card["button"].config(state="normal", text="Заблокировать", cursor="hand2", bg=PANEL, fg=LOCKED_COLOR,
                                      command=lambda k=key: self.lock_one(k))
            else:
                card["button"].config(state="disabled", text="Доступен", cursor="arrow", bg=PANEL, fg=TEXT)
            self.draw_portrait(key, locked)
        self.all_btn.config(state="normal" if any_locked else "disabled", bg=ACCENT if any_locked else PANEL)
        missing = not all(os.path.isfile(os.path.join(PORTRAITS, k + ".png")) for k in self.cards)
        if missing:
            self.portrait_btn.pack(side="right", padx=(0, 8))
        else:
            self.portrait_btn.pack_forget()
        if not self.profiles:
            self.say("Профили LORT не найдены. Нажмите «Папка…» и укажите SaveGames.", ACCENT)

    # ---------- действия ----------
    def say(self, text, color=MUTED):
        self.message.config(text=text, fg=color)

    def apply(self, keys, locking=False):
        path = self.current()
        if not path or self.data is None:
            return
        if core.game_running():
            messagebox.showwarning("Игра запущена", "Закройте LORT: при выходе игра перезапишет сохранение.")
            return
        data, crlf = core.load(path)
        action = core.lock if locking else core.unlock
        changed = [k for k in keys if action(data, k)]
        if not changed:
            self.say("Изменений нет: герой уже %s." % ("закрыт" if locking else "открыт"))
            return
        try:
            backup = core.make_backup(path)
            core.save(path, data, crlf)
        except OSError as e:
            messagebox.showerror("Ошибка записи", str(e))
            return
        self.refresh()
        self.say("%s: %s. Бэкап: %s. Steam Cloud может подменить сохранение, дождитесь синхронизации."
                 % ("Заблокировано" if locking else "Открыто", ", ".join(self.cards[k]["name"] for k in changed),
                    os.path.basename(backup)), ACCENT if locking else OPEN_COLOR)

    def unlock_one(self, key):
        if key in core.HEROES:
            self.apply([key])

    def lock_one(self, key):
        if key in core.HEROES and messagebox.askyesno(
                "Заблокировать героя",
                "Снова закрыть героя %s?\nБудет убран его челлендж и выданное оружие. "
                "Перед этим создаётся бэкап." % self.cards[key]["name"]):
            self.apply([key], locking=True)

    def unlock_all(self):
        self.apply(list(core.HEROES))

    def restore(self):
        path = self.current()
        backup = path and core.latest_backup(path)
        if not backup:
            self.say("Бэкапов для этого профиля нет.", ACCENT)
            return
        if core.game_running():
            messagebox.showwarning("Игра запущена", "Закройте LORT перед откатом.")
            return
        if messagebox.askyesno("Откат", "Вернуть профиль из %s?" % os.path.basename(backup)):
            shutil.copy2(backup, path)
            self.refresh()
            self.say("Профиль восстановлен из %s." % os.path.basename(backup), OPEN_COLOR)


def main():
    ap = argparse.ArgumentParser(description="LORT Character Unlocker (GUI)")
    ap.add_argument("-s", "--save-dir", help="папка SaveGames (по умолчанию ищется сама)")
    args = ap.parse_args()
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    App(args.save_dir).mainloop()


if __name__ == "__main__":
    sys.exit(main())
