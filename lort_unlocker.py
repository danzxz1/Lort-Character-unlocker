#!/usr/bin/env python3
"""LORT Character Unlocker: открывает героев в сохранении игры LORT.

Работает на Windows, Linux (Steam/Proton) и macOS, нужен только Python 3.8+.
Герой считается открытым, когда GUID его «классового» челленджа лежит в
completedChallenges профиля. Для части героев игра дополнительно выдаёт
оружие (unlocks.items), его утилита тоже добавляет.

Перед правкой делается бэкап, игра должна быть закрыта.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

# ключ -> (имя героя, челлендж, GUID челленджа, оружие, которое выдаёт челлендж)
HEROES = {
    "monk": ("Xavier (Monk)", "Challenge_FindTheMonk", "AAD36C394364678D7FB5318010EBD613", ["Weapon_DragonFists"]),
    "rogue": ("Croaks Malone (Rogue)", "Challenge_FindTheRogue", "451C374B418EAE501BA332B944EAA24F", ["Weapon_Blinkblades"]),
    "paladin": ("Marcus T. Fury (Paladin)", "Challenge_Paladin", "E2CD8AA645E8787695EFC5ADC5B4762A", []),
    "wizard": ("Bernie Blazington (Wizard)", "Challenge_MeetBoss_Ranger", "8B2CC76A4C78BC26DE12979CF2AD306C", []),
    "icemage": ("Stacy of Chillendell (IceMage)", "Challenge_Die", "E64C555D44BCE8D7E3136F8CF594DE4A", ["Weapon_IceStaff"]),
}
ALWAYS_OPEN = ["Astrid Glitzgore (Warrior)", "Cliff Bowman (Ranger)"]

PROFILE_RE = re.compile(r"^Profile\d+\.sav$")
BACKUP_MARK = ".bak-"
GAME_PROCESSES = ("LortGame-Win64-Shipping.exe", "LortGame.exe", "LortGame")


def find_save_roots():
    """Возвращает список папок SaveGames, где есть данные LORT."""
    candidates = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(os.path.join(local, "LORT", "Saved", "SaveGames"))
    home = os.path.expanduser("~")
    steam_roots = [
        os.path.join(home, ".local", "share", "Steam"),
        os.path.join(home, ".steam", "steam"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", ".local", "share", "Steam"),
        os.path.join(home, "Library", "Application Support", "Steam"),
    ]
    tail = os.path.join("pfx", "drive_c", "users", "steamuser", "AppData", "Local", "LORT", "Saved", "SaveGames")
    for root in steam_roots:
        candidates += glob.glob(os.path.join(root, "steamapps", "compatdata", "*", tail))
    return [c for c in dict.fromkeys(candidates) if os.path.isdir(c)]


def find_profiles(save_dir):
    """Ищет Profile<N>.sav (без резервных Profile1_1.sav): save_dir или его подпапки Steam ID."""
    found = []
    for base, _dirs, files in os.walk(save_dir):
        found += [os.path.join(base, f) for f in files if PROFILE_RE.match(f)]
    return sorted(found)


def game_running():
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
            return any(p.lower() in out for p in GAME_PROCESSES)
        out = subprocess.run(["ps", "-A", "-o", "comm"], capture_output=True, text=True).stdout
        return any(line.strip().startswith("LortGame") for line in out.splitlines())
    except OSError:
        return False


def load(path):
    with open(path, "rb") as f:
        raw = f.read()
    crlf = b"\r\n" in raw
    return json.loads(raw.decode("utf-8-sig")), crlf


def save(path, data, crlf):
    text = json.dumps(data, indent="\t", ensure_ascii=False)
    if crlf:
        text = text.replace("\n", "\r\n")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def is_open(data, key):
    return HEROES[key][2] in data.get("completedChallenges", [])


def unlock(data, key):
    """Добавляет в профиль всё, что нужно для героя. Возвращает True, если что-то изменилось."""
    _name, _challenge, guid, items = HEROES[key]
    changed = False
    done = data.setdefault("completedChallenges", [])
    if guid not in done:
        done.append(guid)
        changed = True
    unlocked = data.setdefault("unlocks", {}).setdefault("items", [])
    have = {e.get("iD") for e in unlocked}
    for item in items:
        if item not in have:
            unlocked.append({"iD": item, "guid": guid})
            changed = True
    return changed


def lock(data, key):
    """Обратное действие: убирает GUID челленджа и выданное им оружие. True, если что-то изменилось."""
    _name, _challenge, guid, items = HEROES[key]
    changed = False
    done = data.get("completedChallenges", [])
    if guid in done:
        done[:] = [g for g in done if g != guid]
        changed = True
    unlocked = data.get("unlocks", {}).get("items", [])
    kept = [e for e in unlocked if not (e.get("guid") == guid and e.get("iD") in items)]
    if len(kept) != len(unlocked):
        unlocked[:] = kept
        changed = True
    return changed


def make_backup(path):
    dst = "%s%s%s" % (path, BACKUP_MARK, time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, dst)
    return dst


def latest_backup(path):
    backups = sorted(glob.glob(glob.escape(path) + BACKUP_MARK + "*"))
    return backups[-1] if backups else None


def print_status(profiles):
    for p in profiles:
        data, _ = load(p)
        print("\n%s" % p)
        for key, (name, *_rest) in HEROES.items():
            print("  [%s] %-8s %s" % ("x" if is_open(data, key) else " ", key, name))
        for name in ALWAYS_OPEN:
            print("  [x] %-8s %s (открыт по умолчанию)" % ("-", name))


def choose_heroes_interactive(locking=False):
    keys = list(HEROES)
    print("\nКого %s?" % ("заблокировать" if locking else "разблокировать"))
    for i, key in enumerate(keys, 1):
        print("  %d) %-8s %s" % (i, key, HEROES[key][0]))
    print("  a) всех     q) выход")
    answer = input("Номера через пробел или запятую: ").strip().lower()
    if answer in ("", "q"):
        return []
    if answer == "a":
        return keys
    picked = []
    for token in re.split(r"[\s,]+", answer):
        if token.isdigit() and 1 <= int(token) <= len(keys):
            picked.append(keys[int(token) - 1])
        elif token in HEROES:
            picked.append(token)
        else:
            sys.exit("Не понимаю: %r" % token)
    return list(dict.fromkeys(picked))


def choose_profile_interactive(profiles):
    if len(profiles) == 1:
        return profiles
    print("\nНайдено профилей:")
    for i, p in enumerate(profiles, 1):
        print("  %d) %s" % (i, p))
    answer = input("Номер профиля (a — все): ").strip().lower()
    if answer == "a":
        return profiles
    if answer.isdigit() and 1 <= int(answer) <= len(profiles):
        return [profiles[int(answer) - 1]]
    sys.exit("Профиль не выбран.")


def main():
    ap = argparse.ArgumentParser(description="Разблокировка героев LORT в сохранении.")
    ap.add_argument("-s", "--save-dir", help="папка SaveGames или папка со Steam ID (по умолчанию ищется сама)")
    ap.add_argument("-p", "--profile", help="файл профиля, например Profile1.sav (по умолчанию спросит)")
    ap.add_argument("-H", "--hero", action="append", choices=list(HEROES), help="герой (можно несколько раз)")
    ap.add_argument("-a", "--all", action="store_true", help="разблокировать всех героев")
    ap.add_argument("-L", "--lock", action="store_true", help="наоборот: заблокировать выбранных героев")
    ap.add_argument("-l", "--list", action="store_true", help="показать, кто открыт, и выйти")
    ap.add_argument("-n", "--dry-run", action="store_true", help="ничего не записывать")
    ap.add_argument("--restore", action="store_true", help="вернуть профиль из последнего бэкапа")
    ap.add_argument("--force", action="store_true", help="не проверять, что игра закрыта")
    args = ap.parse_args()

    roots = [args.save_dir] if args.save_dir else find_save_roots()
    if not roots:
        sys.exit("Папка сохранений LORT не найдена, укажите её через --save-dir.")
    profiles = [p for r in roots for p in find_profiles(r)]
    if not profiles:
        sys.exit("Файлы Profile<N>.sav не найдены в: %s" % ", ".join(roots))

    if args.profile:
        profiles = [p for p in profiles if os.path.basename(p).lower() == args.profile.lower()]
        if not profiles:
            sys.exit("Профиль %s не найден." % args.profile)

    if args.list:
        print_status(profiles)
        return

    if not args.force and not args.dry_run and game_running():
        sys.exit("Игра запущена. Закройте LORT: при выходе она перезапишет сохранение.")

    interactive = not (args.hero or args.all or args.restore)
    if not args.profile and len(profiles) > 1 and (interactive or args.restore):
        profiles = choose_profile_interactive(profiles)
    elif not args.profile and len(profiles) > 1:
        # неинтерактивный запуск без -p: берём активные (непустые) профили
        profiles = [p for p in profiles if load(p)[0].get("completedChallenges")] or profiles[:1]

    if args.restore:
        for p in profiles:
            backup = latest_backup(p)
            if not backup:
                print("%s: бэкапов нет" % p)
            elif args.dry_run:
                print("%s: был бы восстановлен из %s" % (p, backup))
            else:
                shutil.copy2(backup, p)
                print("%s: восстановлен из %s" % (p, backup))
        return

    if interactive:
        print_status(profiles)
        heroes = choose_heroes_interactive(args.lock)
    else:
        heroes = list(HEROES) if args.all else list(dict.fromkeys(args.hero))
    if not heroes:
        print("Ничего не выбрано.")
        return

    action = lock if args.lock else unlock
    verb = ("заблокированы", "были бы заблокированы") if args.lock else ("открыты", "были бы открыты")
    for p in profiles:
        data, crlf = load(p)
        changed = [k for k in heroes if action(data, k)]
        if not changed:
            print("%s: изменений нет (выбранные герои уже %s)" % (p, "закрыты" if args.lock else "открыты"))
            continue
        names = ", ".join(HEROES[k][0] for k in changed)
        if args.dry_run:
            print("%s: %s: %s" % (p, verb[1], names))
            continue
        backup = make_backup(p)
        save(p, data, crlf)
        print("%s: %s: %s\n  бэкап: %s" % (p, verb[0], names, backup))

    if not args.dry_run:
        print("\nЕсли включён Steam Cloud, отключите синхронизацию на время игры или запускайте игру "
              "только после того, как Steam закончит синхронизацию, иначе облачная копия может перезаписать правку.")


if __name__ == "__main__":
    main()
