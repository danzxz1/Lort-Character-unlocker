#!/usr/bin/env python3
"""Достаёт портреты героев из вашей копии LORT и сохраняет их в portraits/*.png.

Ассеты игры в репозиторий не входят: утилита берёт их у вас локально через retoc
(https://github.com/trumank/retoc) и кладёт обычные PNG рядом со скриптом.

    python extract_portraits.py --retoc path/to/retoc[.exe] [--game-dir <папка LORT>]
"""
import argparse
import glob
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

SIZE = 192  # размер итоговой картинки
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "portraits")

# ключ героя -> имя текстуры в игре
TEXTURES = {
    "warrior": "T_Icon_ClassPortrait_Warrior",
    "ranger": "T_Icon_ClassPortrait_Ranger",
    "wizard": "T_Icon_ClassPortrait_Wizard",
    "rogue": "T_Icon_ClassPortrait_Rogue",
    "monk": "T_Icon_ClassPortrait_Monk_02",
    "icemage": "T_Icon_ClassPortrait_IceMage",
    "paladin": "T_Icons_ClassPortrait_Paladin",
}


def find_game_dir():
    candidates = []
    for root in ("C:", "D:", "E:", "F:", "G:", "H:"):
        candidates.append(os.path.join(root + os.sep, "SteamLibrary", "steamapps", "common", "LORT"))
        candidates.append(os.path.join(root + os.sep, "Program Files (x86)", "Steam", "steamapps", "common", "LORT"))
    home = os.path.expanduser("~")
    for base in (".local/share/Steam", ".steam/steam", "Library/Application Support/Steam"):
        candidates.append(os.path.join(home, base, "steamapps", "common", "LORT"))
    for c in candidates:
        if os.path.isdir(os.path.join(c, "BW", "Content", "Paks")):
            return c
    return None


# ---------- декодеры текстур (чистый Python) ----------

def rgb565(c):
    r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
    return (r * 255 // 31, g * 255 // 63, b * 255 // 31)


def dxt_color_table(c0, c1, allow_alpha):
    p0, p1 = rgb565(c0), rgb565(c1)
    if c0 > c1 or not allow_alpha:
        p2 = tuple((2 * a + b) // 3 for a, b in zip(p0, p1))
        p3 = tuple((a + 2 * b) // 3 for a, b in zip(p0, p1))
        return [p0 + (255,), p1 + (255,), p2 + (255,), p3 + (255,)]
    p2 = tuple((a + b) // 2 for a, b in zip(p0, p1))
    return [p0 + (255,), p1 + (255,), p2 + (255,), (0, 0, 0, 0)]


def decode_dxt(data, w, h, dxt5):
    """Возвращает bytearray RGBA."""
    out = bytearray(w * h * 4)
    step = 16 if dxt5 else 8
    pos = 0
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            alphas = None
            if dxt5:
                a0, a1 = data[pos], data[pos + 1]
                bits = int.from_bytes(data[pos + 2:pos + 8], "little")
                if a0 > a1:
                    table = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
                else:
                    table = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
                alphas = [table[(bits >> (3 * i)) & 7] for i in range(16)]
                cpos = pos + 8
            else:
                cpos = pos
            c0, c1, idx = struct.unpack_from("<HHI", data, cpos)
            colors = dxt_color_table(c0, c1, not dxt5)
            for i in range(16):
                r, g, b, a = colors[(idx >> (2 * i)) & 3]
                if alphas:
                    a = alphas[i]
                o = ((by + i // 4) * w + bx + i % 4) * 4
                out[o:o + 4] = bytes((r, g, b, a))
            pos += step
    return out


def decode_bgra(data, w, h):
    out = bytearray(w * h * 4)
    out[0::4] = data[2:w * h * 4:4]
    out[1::4] = data[1:w * h * 4:4]
    out[2::4] = data[0:w * h * 4:4]
    out[3::4] = data[3:w * h * 4:4]
    return out


def read_texture(uexp_path):
    b = open(uexp_path, "rb").read()
    m = re.search(rb"PF_[A-Za-z0-9_]+", b)
    fmt = m.group().decode()
    w, h = struct.unpack_from("<ii", b, m.start() - 16)
    size = {"PF_B8G8R8A8": w * h * 4, "PF_DXT1": w * h // 2, "PF_DXT5": w * h}[fmt]
    start = m.end() + 1 + 12
    data = b[start:start + size]
    if len(data) != size:
        raise ValueError("%s: неожиданный размер данных" % uexp_path)
    if fmt == "PF_B8G8R8A8":
        return w, h, decode_bgra(data, w, h)
    return w, h, decode_dxt(data, w, h, fmt == "PF_DXT5")


# ---------- обработка картинки и PNG ----------

def resize(rgba, w, h, size):
    """Усреднение по площади, с учётом альфы."""
    out = bytearray(size * size * 4)
    sx, sy = w / size, h / size
    for y in range(size):
        y0, y1 = int(y * sy), max(int(y * sy) + 1, int((y + 1) * sy))
        for x in range(size):
            x0, x1 = int(x * sx), max(int(x * sx) + 1, int((x + 1) * sx))
            r = g = b = a = n = 0
            for yy in range(y0, y1):
                row = yy * w
                for xx in range(x0, x1):
                    o = (row + xx) * 4
                    pa = rgba[o + 3]
                    r += rgba[o] * pa
                    g += rgba[o + 1] * pa
                    b += rgba[o + 2] * pa
                    a += pa
                    n += 1
            o = (y * size + x) * 4
            if a:
                out[o:o + 3] = bytes((r // a, g // a, b // a))
            out[o + 3] = a // n
    return out


def to_locked(rgba):
    """Серый затемнённый вариант для закрытых героев."""
    out = bytearray(rgba)
    for o in range(0, len(out), 4):
        gray = (out[o] * 30 + out[o + 1] * 59 + out[o + 2] * 11) // 100 * 45 // 100
        out[o] = out[o + 1] = out[o + 2] = gray
    return out


def write_png(path, rgba, w, h):
    raw = b"".join(b"\x00" + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))

    def chunk(tag, body):
        c = struct.pack(">I", len(body)) + tag + body
        return c + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def extract(retoc, game_dir, log=print):
    paks = os.path.join(game_dir, "BW", "Content", "Paks")
    if not os.path.isdir(paks):
        raise FileNotFoundError("Не найдена папка Paks: %s" % paks)
    os.makedirs(OUT_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        log("Распаковываю текстуры через retoc...")
        res = subprocess.run([retoc, "to-legacy", "--no-shaders", "--no-script-objects",
                              "-f", "ClassPortrait", paks, tmp], capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError("retoc завершился с ошибкой:\n%s" % (res.stderr or res.stdout))
        for key, name in TEXTURES.items():
            hits = glob.glob(os.path.join(tmp, "**", name + ".uexp"), recursive=True)
            if not hits:
                log("  %s: текстура не найдена" % key)
                continue
            w, h, rgba = read_texture(hits[0])
            small = resize(rgba, w, h, SIZE)
            write_png(os.path.join(OUT_DIR, key + ".png"), small, SIZE, SIZE)
            write_png(os.path.join(OUT_DIR, key + "_locked.png"), to_locked(small), SIZE, SIZE)
            log("  %s: готово" % key)
    log("Портреты сохранены в %s" % OUT_DIR)


def main():
    ap = argparse.ArgumentParser(description="Извлечение портретов героев LORT в PNG.")
    ap.add_argument("--retoc", help="путь к retoc (по умолчанию ищется в PATH)")
    ap.add_argument("--game-dir", help="папка игры LORT (по умолчанию ищется в Steam)")
    args = ap.parse_args()
    retoc = args.retoc or shutil.which("retoc")
    if not retoc:
        sys.exit("retoc не найден: скачайте его с https://github.com/trumank/retoc/releases и укажите --retoc.")
    game_dir = args.game_dir or find_game_dir()
    if not game_dir:
        sys.exit("Папка игры не найдена, укажите --game-dir.")
    extract(retoc, game_dir)


if __name__ == "__main__":
    main()
