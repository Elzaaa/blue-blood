"""Blue Blood — кот убегает, лис догоняет. Игра на двоих за одной клавиатурой.

Запуск на компьютере:   python main.py
Сборка для браузера:    pygbag blueblood   (из папки над этой; см. README)
"""
import asyncio
import math
import random

import pygame

import sprites
from logic import (COLS, MAP, ROWS, TILE, BLACKCAT_COOLDOWN, DASH_COOLDOWN,
                   FISH_WIN, FOX_HEARTS, GRAN_COOLDOWN, GRAN_HOLD, SCRATCH_TIME,
                   SNIFF_TIME, WARD_MAX, Game, cell_center)

HUD_H = 52
W, H = COLS * TILE, ROWS * TILE + HUD_H
WINS_NEEDED = 3

# --- управление: у каждого игрока своя сторона клавиатуры --------------
# Используем физические клавиши (scancode) — работает при любой раскладке, хоть русской.
SIDES = [
    dict(up=pygame.KSCAN_W, down=pygame.KSCAN_S, left=pygame.KSCAN_A, right=pygame.KSCAN_D,
         act=(pygame.KSCAN_E, pygame.KSCAN_SPACE), summon=(pygame.KSCAN_Q,),
         names=("WASD", "E", "Q")),
    dict(up=pygame.KSCAN_UP, down=pygame.KSCAN_DOWN, left=pygame.KSCAN_LEFT, right=pygame.KSCAN_RIGHT,
         act=(pygame.KSCAN_PERIOD, pygame.KSCAN_RETURN, pygame.KSCAN_KP_0, pygame.KSCAN_L),
         summon=(pygame.KSCAN_SLASH, pygame.KSCAN_RSHIFT, pygame.KSCAN_KP_1, pygame.KSCAN_K),
         names=("Arrows", ".", "/")),
]
PLAYER = ["Player 1", "Player 2"]

CAT_COL = (222, 172, 128)
FOX_COL = (255, 128, 48)
PINK = (240, 140, 180)

# --- особняк: цвета ---------------------------------------------------------
GOLD = (222, 184, 92)
GOLD_D = (150, 116, 50)
WALL = (58, 40, 48)
WALL_D = (46, 31, 38)
DOOR_C = (120, 58, 44)      # красное дерево
DOOR_D = (74, 34, 28)

WALLPAPER = {
    "kitchen": (214, 200, 166), "salon": (52, 92, 76), "bedroom": (112, 44, 60),
    "hall": (44, 56, 98), "bath": (176, 196, 206), "library": (40, 70, 52), "dining": (122, 40, 40),
}
PARQUET = {
    "salon": ((198, 152, 98), (170, 126, 78)),
    "dining": ((188, 140, 90), (160, 116, 72)),
    "library": ((124, 82, 52), (100, 64, 40)),
}
# украшения на стенах: (колонка, ряд стены) -> что висит
DECOR = {
    (4, 0): "window", (11, 0): "portrait", (14, 0): "fireplace", (19, 0): "portrait", (22, 0): "window",
    (2, 5): "portrait", (6, 5): "sconce", (8, 5): "portrait", (10, 5): "sconce", (14, 5): "sconce",
    (16, 5): "portrait", (18, 5): "sconce", (22, 5): "portrait",
    (5, 9): "mirror", (19, 9): "portrait", (18, 9): "sconce", (21, 9): "sconce",
}
FIREPLACES = [c for c, k in DECOR.items() if k == "fireplace"]
FACE_H = 18   # высота видимой «стенки» с обоями


def room_of(c, r):
    if r <= 4:
        return "kitchen" if c <= 7 else "salon" if c <= 15 else "bedroom"
    if r >= 10:
        return "bath" if c <= 7 else "library" if c <= 15 else "dining"
    return "hall"


def shade(col, d):
    return tuple(max(0, min(255, v + d)) for v in col)


def draw_floor(surf, c, r):
    x, y = c * TILE, r * TILE
    room = room_of(c, r)
    if room == "kitchen":      # терракотовая плитка
        for i in range(2):
            for j in range(2):
                col = (196, 108, 76) if (i + j) % 2 == 0 else (182, 96, 66)
                pygame.draw.rect(surf, col, (x + i * 16, y + j * 16, 16, 16))
                pygame.draw.rect(surf, (150, 80, 56), (x + i * 16, y + j * 16, 16, 16), 1)
    elif room == "hall":       # мраморные шашечки
        for i in range(2):
            for j in range(2):
                light = (c * 2 + i + r * 2 + j) % 2 == 0
                col = (232, 228, 220) if light else (58, 54, 66)
                pygame.draw.rect(surf, col, (x + i * 16, y + j * 16, 16, 16))
                if light and (c + r + i) % 3 == 0:
                    pygame.draw.line(surf, (200, 196, 190), (x + i * 16 + 3, y + j * 16 + 12),
                                     (x + i * 16 + 12, y + j * 16 + 5))
    elif room == "bath":       # белый мрамор с прожилками
        pygame.draw.rect(surf, (236, 238, 240), (x, y, TILE, TILE))
        rnd = random.Random(c * 13 + r * 7)
        for _ in range(2):
            x1, y1 = x + rnd.randint(0, 31), y + rnd.randint(0, 31)
            pygame.draw.line(surf, (204, 208, 216), (x1, y1),
                             (min(x + 31, x1 + rnd.randint(4, 14)), min(y + 31, y1 + rnd.randint(-6, 8))))
        pygame.draw.rect(surf, (214, 218, 224), (x, y, TILE, TILE), 1)
    elif room == "bedroom":    # ковёр с узором
        pygame.draw.rect(surf, (118, 42, 58), (x, y, TILE, TILE))
        for i in range(4):
            for j in range(4):
                if (i + j) % 2 == 0:
                    pygame.draw.rect(surf, (142, 62, 74), (x + i * 8 + 3, y + j * 8 + 3, 2, 2))
    else:                      # паркет-плетёнка
        light, dark = PARQUET[room]
        for i in range(2):
            for j in range(2):
                bx, by = x + i * 16, y + j * 16
                pygame.draw.rect(surf, light, (bx, by, 16, 16))
                if (c * 2 + i + r * 2 + j) % 2 == 0:
                    for k in (5, 10):
                        pygame.draw.line(surf, dark, (bx, by + k), (bx + 15, by + k))
                else:
                    for k in (5, 10):
                        pygame.draw.line(surf, dark, (bx + k, by), (bx + k, by + 15))
                pygame.draw.rect(surf, dark, (bx, by, 16, 16), 1)


def draw_rug(surf, rect, base, border, accent):
    pygame.draw.rect(surf, border, rect)
    inner = rect.inflate(-10, -10)
    pygame.draw.rect(surf, base, inner)
    pygame.draw.rect(surf, accent, inner.inflate(-6, -6), 1)
    cx, cy = inner.center
    s = min(inner.w, inner.h) // 3
    pygame.draw.polygon(surf, accent, [(cx, cy - s), (cx + s * 1.4, cy), (cx, cy + s), (cx - s * 1.4, cy)], 2)
    pygame.draw.polygon(surf, border, [(cx, cy - s // 2), (cx + s * 0.7, cy), (cx, cy + s // 2), (cx - s * 0.7, cy)])
    for k in range(rect.x + 2, rect.right - 2, 4):     # бахрома
        pygame.draw.line(surf, (230, 220, 200), (k, rect.y - 3), (k, rect.y))
        pygame.draw.line(surf, (230, 220, 200), (k, rect.bottom), (k, rect.bottom + 3))


def draw_wall(surf, c, r):
    x, y = c * TILE, r * TILE
    pygame.draw.rect(surf, WALL, (x, y, TILE, TILE))
    for k in range(0, TILE, 8):
        pygame.draw.line(surf, WALL_D, (x, y + k), (x + TILE, y + k))
    if r + 1 >= ROWS or MAP[r + 1][c] == "#":
        return
    paper = WALLPAPER[room_of(c, r + 1)]
    fy = y + TILE - FACE_H
    pygame.draw.rect(surf, paper, (x, fy, TILE, FACE_H))
    for k in range(3, TILE, 6):
        pygame.draw.line(surf, shade(paper, -16), (x + k, fy + 2), (x + k, y + TILE - 5))
        pygame.draw.circle(surf, shade(paper, 14), (x + k, fy + 7), 1)
    pygame.draw.line(surf, GOLD, (x, fy), (x + TILE, fy))
    pygame.draw.rect(surf, (70, 40, 32), (x, y + TILE - 4, TILE, 4))     # плинтус
    kind = DECOR.get((c, r))
    if kind == "portrait":
        rnd = random.Random(c * 7 + r)
        fr = pygame.Rect(x + 8, fy - 6, 16, 19)
        pygame.draw.rect(surf, GOLD, fr)
        pygame.draw.rect(surf, GOLD_D, fr, 1)
        inner = fr.inflate(-4, -4)
        pygame.draw.rect(surf, rnd.choice([(40, 46, 70), (60, 36, 40), (36, 56, 44)]), inner)
        pygame.draw.ellipse(surf, rnd.choice([(80, 60, 50), (210, 210, 220), (150, 110, 60)]),
                            (inner.x + 2, inner.y + 1, inner.w - 4, 8))
        pygame.draw.ellipse(surf, (236, 200, 170), (inner.x + 4, inner.y + 3, inner.w - 8, 7))
        pygame.draw.rect(surf, rnd.choice([(30, 30, 40), (120, 40, 60), (40, 60, 120)]),
                         (inner.x + 1, inner.y + 10, inner.w - 2, inner.h - 10))
    elif kind == "sconce":
        pygame.draw.rect(surf, GOLD, (x + 13, fy + 6, 6, 3))
        pygame.draw.rect(surf, (250, 246, 230), (x + 15, fy + 1, 2, 5))
        pygame.draw.circle(surf, (255, 220, 120), (x + 16, fy), 2)
    elif kind == "window":
        fr = pygame.Rect(x + 6, fy - 8, 20, 22)
        pygame.draw.rect(surf, (70, 40, 32), fr)
        pygame.draw.rect(surf, (156, 196, 232), fr.inflate(-4, -4))
        pygame.draw.line(surf, (70, 40, 32), (fr.centerx, fr.y), (fr.centerx, fr.bottom))
        pygame.draw.line(surf, (70, 40, 32), (fr.x, fr.centery), (fr.right, fr.centery))
        pygame.draw.rect(surf, (140, 30, 46), (x + 2, fy - 9, 6, 24))     # шторы
        pygame.draw.rect(surf, (140, 30, 46), (x + 24, fy - 9, 6, 24))
        pygame.draw.line(surf, GOLD, (x + 1, fy - 10), (x + 31, fy - 10), 2)
    elif kind == "mirror":
        fr = pygame.Rect(x + 7, fy - 8, 18, 21)
        pygame.draw.ellipse(surf, GOLD, fr)
        pygame.draw.ellipse(surf, (200, 214, 226), fr.inflate(-5, -5))
        pygame.draw.line(surf, (240, 246, 250), (fr.x + 7, fr.y + 6), (fr.x + 10, fr.y + 3), 2)
    elif kind == "fireplace":
        pygame.draw.rect(surf, (206, 196, 180), (x + 1, y + 6, 30, TILE - 6))
        pygame.draw.rect(surf, (170, 160, 146), (x + 1, y + 6, 30, TILE - 6), 1)
        pygame.draw.rect(surf, (226, 218, 204), (x - 1, y + 5, 34, 4))      # полка
        pygame.draw.rect(surf, (24, 18, 18), (x + 8, y + 14, 16, TILE - 14))
        pygame.draw.rect(surf, GOLD, (x + 7, y + 13, 18, 2))


def run_len(c, r, ch):
    n = 0
    while c + n < COLS and MAP[r][c + n] == ch:
        n += 1
    return n


def draw_furniture(surf, c, r, ch):
    x, y = c * TILE, r * TILE
    room = room_of(c, r)
    if ch == "f" and room == "kitchen" and r == 1:            # мраморная столешница
        pygame.draw.rect(surf, (226, 214, 184), (x, y, TILE, TILE - 2))
        pygame.draw.rect(surf, (150, 130, 100), (x, y, TILE, TILE - 2), 1)
        pygame.draw.rect(surf, (228, 228, 234), (x, y, TILE, 9))
        pygame.draw.line(surf, (190, 190, 200), (x, y + 9), (x + TILE, y + 9))
        pygame.draw.circle(surf, GOLD, (x + 16, y + 18), 2)
        if c == 6:                                           # плита
            pygame.draw.rect(surf, (40, 40, 46), (x + 2, y + 1, 28, 8))
            pygame.draw.circle(surf, (90, 90, 100), (x + 9, y + 5), 3, 1)
            pygame.draw.circle(surf, (90, 90, 100), (x + 22, y + 5), 3, 1)
    elif ch == "f" and room == "kitchen":                    # кухонный стол
        pygame.draw.rect(surf, (90, 56, 34), (x + 3, y + 6, 26, 22))
        pygame.draw.rect(surf, (156, 106, 64), (x + 3, y + 4, 26, 20))
        pygame.draw.rect(surf, (240, 236, 226), (x + 9, y + 8, 14, 10), border_radius=3)
        pygame.draw.ellipse(surf, (210, 160, 90), (x + 11, y + 9, 10, 7))
    elif ch == "f" and room == "library":                    # книжный стеллаж
        rnd = random.Random(c * 5 + r)
        sh = pygame.Rect(x + 1, y - 8, 30, TILE + 6)
        pygame.draw.rect(surf, (64, 38, 26), sh)
        for row in range(3):
            yy = sh.y + 3 + row * 11
            xx = sh.x + 3
            while xx < sh.right - 4:
                w = rnd.randint(2, 4)
                h = rnd.randint(6, 9)
                col = rnd.choice([(150, 40, 40), (40, 70, 130), (50, 110, 60), (190, 150, 60), (110, 60, 120)])
                pygame.draw.rect(surf, col, (xx, yy + 9 - h, w, h))
                xx += w + 1
            pygame.draw.line(surf, (96, 60, 40), (sh.x, yy + 9), (sh.right - 1, yy + 9), 2)
    elif ch == "f" and room == "dining" and r == 11:         # длинный обеденный стол
        if c > 0 and MAP[r][c - 1] == "f":
            return
        n = run_len(c, r, "f")
        tab = pygame.Rect(x + 2, y + 2, n * TILE - 4, TILE - 4)
        pygame.draw.rect(surf, (90, 50, 30), tab.move(0, 3))
        pygame.draw.rect(surf, (246, 244, 238), tab, border_radius=3)
        pygame.draw.line(surf, (214, 210, 200), (tab.x, tab.bottom - 3), (tab.right, tab.bottom - 3))
        for k in range(n):
            px = x + k * TILE + 16
            pygame.draw.circle(surf, (230, 230, 236), (px, y + 9), 5)
            pygame.draw.circle(surf, (200, 200, 210), (px, y + 9), 5, 1)
            pygame.draw.circle(surf, (230, 230, 236), (px, y + 23), 5)
            pygame.draw.circle(surf, (200, 200, 210), (px, y + 23), 5, 1)
        cx = tab.centerx
        pygame.draw.rect(surf, GOLD, (cx - 7, y + 15, 14, 3))
        for dx in (-6, 0, 6):
            pygame.draw.rect(surf, (250, 248, 236), (cx + dx - 1, y + 8, 2, 7))
            pygame.draw.circle(surf, (255, 200, 80), (cx + dx, y + 7), 2)
    elif ch == "f" and room == "salon":                      # кресло
        pygame.draw.rect(surf, (30, 60, 46), (x + 4, y + 4, 24, 25), border_radius=6)
        pygame.draw.rect(surf, (52, 110, 80), (x + 5, y + 3, 22, 23), border_radius=6)
        pygame.draw.rect(surf, (40, 90, 64), (x + 5, y + 3, 22, 8), border_radius=6)
        pygame.draw.rect(surf, (70, 136, 100), (x + 9, y + 12, 14, 10), border_radius=3)
        pygame.draw.rect(surf, GOLD, (x + 6, y + 27, 3, 3))
        pygame.draw.rect(surf, GOLD, (x + 23, y + 27, 3, 3))
    elif ch == "f":                                          # комод
        pygame.draw.rect(surf, (60, 28, 22), (x + 2, y + 4, 28, 26), border_radius=2)
        pygame.draw.rect(surf, (118, 56, 42), (x + 3, y + 3, 26, 24), border_radius=2)
        for k in (10, 18):
            pygame.draw.line(surf, (80, 36, 28), (x + 4, y + k), (x + 27, y + k))
            pygame.draw.circle(surf, GOLD, (x + 16, y + k + 4), 1)
        pygame.draw.ellipse(surf, (210, 214, 224), (x + 8, y + 1, 16, 6))
    elif ch == "v":                                          # мраморный постамент
        pygame.draw.rect(surf, (170, 170, 178), (x + 9, y + 26, 14, 4))
        pygame.draw.rect(surf, (236, 236, 240), (x + 11, y + 14, 10, 13))
        pygame.draw.line(surf, (200, 200, 208), (x + 15, y + 15), (x + 15, y + 25))
        pygame.draw.ellipse(surf, (170, 170, 178), (x + 5, y + 11, 22, 7))
        pygame.draw.ellipse(surf, (244, 244, 248), (x + 5, y + 10, 22, 6))
    elif ch == "s":                                          # диван-честерфилд
        pygame.draw.rect(surf, (70, 20, 30), (x - 6, y + 3, 44, 27), border_radius=7)
        pygame.draw.rect(surf, (134, 36, 52), (x - 5, y + 2, 42, 24), border_radius=7)
        pygame.draw.rect(surf, (112, 28, 44), (x - 5, y + 2, 42, 9), border_radius=7)
        for k in range(4):
            pygame.draw.circle(surf, (90, 22, 36), (x - 1 + k * 11, y + 16), 1)
        pygame.draw.rect(surf, GOLD, (x - 3, y + 27, 3, 3))
        pygame.draw.rect(surf, GOLD, (x + 32, y + 27, 3, 3))
    elif ch == "b":                                          # кровать с балдахином
        if (c > 0 and MAP[r][c - 1] == "b") or (r > 0 and MAP[r - 1][c] == "b"):
            return
        w = run_len(c, r, "b")
        h = 0
        while MAP[r + h][c] == "b":
            h += 1
        bed = pygame.Rect(x + 2, y + 2, w * TILE - 4, h * TILE - 4)
        pygame.draw.rect(surf, (60, 30, 22), bed)
        pygame.draw.rect(surf, (238, 236, 230), bed.inflate(-6, -6))
        blanket = pygame.Rect(bed.x + 3, bed.y + 24, bed.w - 6, bed.h - 27)
        pygame.draw.rect(surf, (128, 30, 50), blanket)
        pygame.draw.rect(surf, GOLD, blanket, 2)
        pygame.draw.line(surf, GOLD, (blanket.x, blanket.y + 8), (blanket.right - 1, blanket.y + 8))
        for k in range(2):
            pygame.draw.rect(surf, (250, 250, 252), (bed.x + 6 + k * (bed.w // 2 - 2), bed.y + 6,
                                                     bed.w // 2 - 10, 14), border_radius=4)
        for px, py in ((bed.x, bed.y), (bed.right - 5, bed.y), (bed.x, bed.bottom - 5), (bed.right - 5, bed.bottom - 5)):
            pygame.draw.rect(surf, (90, 46, 30), (px, py, 5, 5))
            pygame.draw.circle(surf, GOLD, (px + 2, py + 2), 1)
    elif ch == "p":                                          # пальма в фарфоровом горшке
        pygame.draw.rect(surf, (236, 238, 244), (x + 10, y + 19, 12, 11), border_radius=2)
        pygame.draw.line(surf, (60, 90, 170), (x + 10, y + 23), (x + 21, y + 23), 2)
        for a in range(7):
            ang = math.pi + a * math.pi / 6
            ex, ey = x + 16 + math.cos(ang) * 13, y + 16 + math.sin(ang) * 11
            pygame.draw.line(surf, (40, 120, 60), (x + 16, y + 19), (ex, ey), 3)
            pygame.draw.line(surf, (80, 170, 90), (x + 16, y + 19), (ex, ey), 1)


def build_background():
    bg = pygame.Surface((COLS * TILE, ROWS * TILE))
    for r in range(ROWS):
        for c in range(COLS):
            if MAP[r][c] != "#":
                draw_floor(bg, c, r)
    # ковры
    draw_rug(bg, pygame.Rect(10 * TILE + 4, 2 * TILE + 2, 5 * TILE - 8, 3 * TILE - 6),
             (140, 36, 44), (40, 50, 100), GOLD)
    draw_rug(bg, pygame.Rect(18 * TILE + 2, 10 * TILE + 8, 5 * TILE - 4, 3 * TILE - 16),
             (40, 56, 110), (120, 30, 40), GOLD)
    runner = pygame.Rect(TILE, 7 * TILE + 6, (COLS - 2) * TILE, TILE - 12)
    pygame.draw.rect(bg, (146, 30, 42), runner)
    pygame.draw.rect(bg, GOLD, runner.inflate(0, -4), 1)
    for r in range(ROWS):
        for c in range(COLS):
            if MAP[r][c] == "#":
                draw_wall(bg, c, r)
    for r in range(ROWS):
        for c in range(COLS):
            if MAP[r][c] in "fvspb":
                draw_furniture(bg, c, r, MAP[r][c])
    return bg


def draw_fire(surf, t):
    for c, r in FIREPLACES:
        x, y = c * TILE + 16, r * TILE + HUD_H + TILE - 3
        for k in range(3):
            h = 7 + math.sin(t * 13 + k * 2.1) * 3
            col = [(255, 120, 30), (255, 180, 50), (255, 240, 150)][k]
            w = 6 - k * 2
            pygame.draw.polygon(surf, col, [(x - w - 1, y), (x + w + 1, y), (x + math.sin(t * 9 + k) * 2, y - h + k * 2)])



# --- прежнее оформление «Дом» (переключается клавишей T в меню) -------------
STYLE = {"name": "manor"}       # "manor" — особняк, "classic" — простой дом
CLASSIC_DOOR = ((150, 86, 40), (110, 60, 28), (240, 210, 90))
MANOR_DOOR = (DOOR_C, DOOR_D, GOLD)


def build_background_classic():
    wood, wood_d = (214, 186, 140), (190, 160, 116)
    tile_a, tile_b = (206, 210, 220), (178, 186, 202)
    wall, wall_top = (66, 54, 78), (104, 88, 120)

    def kind(c, r):
        ch = MAP[r][c]
        if ch in ".,":
            return ch
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= c + dc < COLS and 0 <= r + dr < ROWS and MAP[r + dr][c + dc] in ".,":
                return MAP[r + dr][c + dc]
        return "."

    bg = pygame.Surface((COLS * TILE, ROWS * TILE))
    for r in range(ROWS):
        for c in range(COLS):
            ch = MAP[r][c]
            x, y = c * TILE, r * TILE
            if ch == "#":
                pygame.draw.rect(bg, wall, (x, y, TILE, TILE))
                for k in range(0, TILE, 8):
                    pygame.draw.line(bg, (56, 46, 66), (x, y + k), (x + TILE, y + k))
                    off = 8 if (k // 8 + c) % 2 else 0
                    pygame.draw.line(bg, (56, 46, 66), (x + off + 4, y + k), (x + off + 4, y + k + 8))
                    pygame.draw.line(bg, (56, 46, 66), (x + off + 20, y + k), (x + off + 20, y + k + 8))
                if r + 1 < ROWS and MAP[r + 1][c] != "#":
                    pygame.draw.rect(bg, wall_top, (x, y + TILE - 6, TILE, 6))
                continue
            if kind(c, r) == ",":
                for i in range(2):
                    for j in range(2):
                        col = tile_a if (i + j) % 2 == 0 else tile_b
                        pygame.draw.rect(bg, col, (x + i * 16, y + j * 16, 16, 16))
            else:
                rnd = random.Random(c * 97 + r * 31)
                pygame.draw.rect(bg, wood, (x, y, TILE, TILE))
                for k in range(4):
                    yy = y + k * 8
                    pygame.draw.line(bg, wood_d, (x, yy), (x + TILE, yy))
                    off = rnd.randint(0, TILE)
                    pygame.draw.line(bg, wood_d, (x + off, yy), (x + off, yy + 8))
            if ch == "f":
                pygame.draw.rect(bg, (60, 40, 24), (x + 2, y + 4, 28, 26), border_radius=3)
                pygame.draw.rect(bg, (140, 92, 52), (x + 3, y + 3, 26, 24), border_radius=3)
                pygame.draw.rect(bg, (176, 124, 76), (x + 3, y + 3, 26, 6), border_radius=3)
                pygame.draw.circle(bg, (230, 200, 120), (x + 16, y + 18), 2)
            elif ch == "v":
                pygame.draw.rect(bg, (90, 56, 30), (x + 14, y + 18, 4, 12))
                pygame.draw.ellipse(bg, (60, 40, 24), (x + 2, y + 13, 28, 12))
                pygame.draw.ellipse(bg, (170, 112, 64), (x + 3, y + 12, 26, 10))
            elif ch == "s":
                pygame.draw.rect(bg, (90, 30, 40), (x + 1, y + 6, 30, 24), border_radius=6)
                pygame.draw.rect(bg, (190, 60, 70), (x + 2, y + 5, 28, 22), border_radius=6)
                pygame.draw.rect(bg, (220, 90, 100), (x + 6, y + 8, 20, 10), border_radius=4)
            elif ch == "b":
                pygame.draw.rect(bg, (40, 50, 90), (x + 1, y + 1, 30, 30))
                pygame.draw.rect(bg, (80, 110, 200), (x + 2, y + 2, 28, 28))
                if r > 0 and MAP[r - 1][c] == "#":
                    pygame.draw.rect(bg, (245, 245, 250), (x + 5, y + 4, 22, 10), border_radius=4)
            elif ch == "p":
                pygame.draw.rect(bg, (150, 70, 40), (x + 10, y + 18, 12, 11))
                pygame.draw.circle(bg, (30, 110, 50), (x + 16, y + 13), 10)
                pygame.draw.circle(bg, (60, 160, 70), (x + 13, y + 10), 5)
    return bg


def draw_door(surf, d, t):
    DOOR_C, DOOR_D, KNOB = MANOR_DOOR if STYLE["name"] == "manor" else CLASSIC_DOOR
    x, y = d.c * TILE, d.r * TILE + HUD_H
    if d.open:
        if d.horizontal:
            pygame.draw.rect(surf, DOOR_D, (x, y, 4, TILE))
            pygame.draw.rect(surf, DOOR_D, (x + TILE - 4, y, 4, TILE))
            pygame.draw.rect(surf, DOOR_C, (x + 4, y, 4, TILE - 6))
        else:
            pygame.draw.rect(surf, DOOR_D, (x, y, TILE, 4))
            pygame.draw.rect(surf, DOOR_D, (x, y + TILE - 4, TILE, 4))
            pygame.draw.rect(surf, DOOR_C, (x, y + 4, TILE - 6, 4))
        return
    shake = 0
    if d.scratch > 0:
        shake = int(math.sin(t * 60) * 2 * min(1, d.scratch / SCRATCH_TIME + 0.3))
    rect = pygame.Rect(x + shake, y, TILE, TILE)
    pygame.draw.rect(surf, DOOR_D, rect)
    pygame.draw.rect(surf, DOOR_C, rect.inflate(-4, -4))
    for k in (10, 21):
        if d.horizontal:
            pygame.draw.line(surf, DOOR_D, (rect.x + k, rect.y + 2), (rect.x + k, rect.bottom - 3))
        else:
            pygame.draw.line(surf, DOOR_D, (rect.x + 2, rect.y + k), (rect.right - 3, rect.y + k))
    pygame.draw.circle(surf, KNOB, (rect.right - 7, rect.centery), 3)
    if d.scratch > 0:
        n = int(d.scratch / SCRATCH_TIME * 4) + 1
        for i in range(n):
            xx = rect.x + 7 + i * 5
            pygame.draw.line(surf, (60, 30, 10), (xx, rect.y + 8), (xx + 4, rect.y + 22), 2)
        bar(surf, x, y - 7, TILE, 5, d.scratch / SCRATCH_TIME, FOX_COL)


def draw_wardrobe(surf, w, i, t, rustle):
    x, y = w.c * TILE, w.r * TILE + HUD_H
    if rustle:
        x += int(math.sin(t * 23 + i * 1.9) * 1.6)
    body = pygame.Rect(x + 2, y - 12, 28, 42)
    if STYLE["name"] == "classic":
        pygame.draw.rect(surf, (54, 34, 20), body, border_radius=2)
        pygame.draw.rect(surf, (128, 82, 46), body.inflate(-4, -4), border_radius=2)
        pygame.draw.rect(surf, (150, 100, 58), (body.x + 2, body.y + 2, body.w - 4, 5))
        pygame.draw.line(surf, (54, 34, 20), (body.centerx, body.y + 8), (body.centerx, body.bottom - 3), 2)
        pygame.draw.circle(surf, (236, 206, 110), (body.centerx - 4, body.centery + 4), 2)
        pygame.draw.circle(surf, (236, 206, 110), (body.centerx + 4, body.centery + 4), 2)
        if w.sniff > 0:
            bar(surf, x, y - 20, TILE, 5, w.sniff / SNIFF_TIME, FOX_COL)
        return
    pygame.draw.rect(surf, (54, 22, 18), body, border_radius=2)
    pygame.draw.rect(surf, (116, 50, 38), body.inflate(-4, -4), border_radius=2)
    pygame.draw.rect(surf, (140, 66, 50), (body.x + 1, body.y, body.w - 2, 6))
    pygame.draw.line(surf, GOLD, (body.x + 1, body.y + 6), (body.right - 2, body.y + 6))
    for px in (body.x + 4, body.centerx + 2):
        pygame.draw.rect(surf, (96, 40, 30), (px, body.y + 10, 10, body.h - 15), 1)
    pygame.draw.line(surf, (54, 22, 18), (body.centerx, body.y + 8), (body.centerx, body.bottom - 3), 2)
    pygame.draw.circle(surf, GOLD, (body.centerx - 3, body.centery + 4), 2)
    pygame.draw.circle(surf, GOLD, (body.centerx + 3, body.centery + 4), 2)
    if w.sniff > 0:
        bar(surf, x, y - 20, TILE, 5, w.sniff / SNIFF_TIME, FOX_COL)


def draw_shards(surf, s, t):
    if s.life < 2 and int(t * 10) % 2:
        return
    rnd = random.Random(s.c * 31 + s.r * 7)
    x0, y0 = s.c * TILE, s.r * TILE + HUD_H
    for _ in range(9):
        x, y = x0 + rnd.randint(3, 27), y0 + rnd.randint(3, 27)
        col = rnd.choice([(90, 150, 214), (150, 200, 240), (240, 248, 255)])
        pts = [(x, y), (x + rnd.randint(2, 5), y + rnd.randint(-3, 1)), (x + rnd.randint(-1, 3), y + rnd.randint(2, 5))]
        pygame.draw.polygon(surf, col, pts)


def bar(surf, x, y, w, h, frac, col):
    pygame.draw.rect(surf, (40, 30, 40), (x, y, w, h), border_radius=2)
    pygame.draw.rect(surf, col, (x, y, int(w * max(0.0, min(1.0, frac))), h), border_radius=2)


# --- эффекты -------------------------------------------------------------
class Spot:
    def __init__(self, x, y):
        self.x, self.y = x, y


class Particles:
    def __init__(self):
        self.items = []

    def burst(self, x, y, color, n=14, speed=120, life=0.6, size=3):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(speed * 0.3, speed)
            self.items.append([x, y, math.cos(a) * s, math.sin(a) * s, life, life, color, size])

    def update(self, dt):
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.9
            p[3] *= 0.9
            p[4] -= dt
        self.items = [p for p in self.items if p[4] > 0]

    def draw(self, surf):
        for x, y, _, _, life, total, col, size in self.items:
            s = max(1, int(size * life / total + 0.5))
            pygame.draw.rect(surf, col, (int(x) - s // 2, int(y) + HUD_H - s // 2, s, s))


# --- ввод ----------------------------------------------------------------
def read_side(held, keys, side):
    k = SIDES[side]
    return {
        "dx": (k["right"] in held) - (k["left"] in held),
        "dy": (k["down"] in held) - (k["up"] in held),
        "act": any(x in keys for x in k["act"]),
        "summon": any(x in keys for x in k["summon"]),
    }


class Match:
    """Счёт матча. Роли меняются каждый раунд."""
    def __init__(self):
        self.wins = [0, 0]
        self.cat_player = 0
        self.round = 1
        self.done = False
        self.last = None

    def player_of(self, role):
        return self.cat_player if role == "cat" else 1 - self.cat_player

    def finish_round(self, winner_role):
        self.last = self.player_of(winner_role)
        self.wins[self.last] += 1
        self.done = self.wins[self.last] >= WINS_NEEDED

    def next_round(self):
        self.cat_player = 1 - self.cat_player
        self.round += 1

    def inputs(self, held, keys):
        return {"cat": read_side(held, keys, self.cat_player),
                "fox": read_side(held, keys, 1 - self.cat_player)}


# --- отрисовка -----------------------------------------------------------
class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.bgs = {"manor": build_background(), "classic": build_background_classic()}
        self.spr = sprites.load_all()
        self.f_tiny = pygame.font.Font(None, 19)
        self.f_small = pygame.font.Font(None, 22)
        self.f_mid = pygame.font.Font(None, 30)
        self.f_big = pygame.font.Font(None, 56)
        self.f_huge = pygame.font.Font(None, 120)
        self.fx = Particles()
        self.popups = []
        self.trail = []
        self.shake = 0.0
        self.t = 0.0
        self.heart_t = 0.0
        self.fish_icon = pygame.transform.scale(self.spr["fish"], (18, 10))
        self.fish_icon_dim = self.fish_icon.copy()
        self.fish_icon_dim.set_alpha(60)

    @property
    def bg(self):
        return self.bgs[STYLE["name"]]

    def text(self, s, font, color, center=None, topleft=None, shadow=True):
        img = font.render(s, True, color)
        rect = img.get_rect()
        if center:
            rect.center = center
        if topleft:
            rect.topleft = topleft
        if shadow:
            self.screen.blit(font.render(s, True, (20, 16, 24)), rect.move(2, 2))
        self.screen.blit(img, rect)
        return rect

    def popup(self, s, x, y, col):
        self.popups.append([s, x, y, 1.0, col])

    def reset(self):
        self.fx.items.clear()
        self.popups.clear()
        self.trail.clear()

    def handle_events(self, g):
        for kind, x, y in g.events:
            if kind == "break":
                self.fx.burst(x, y, (150, 86, 40), 22, 160, 0.8, 4)
                self.shake = 0.25
            elif kind == "close":
                self.fx.burst(x, y, (200, 200, 200), 8, 60, 0.3, 2)
            elif kind == "open":
                self.fx.burst(x, y, (230, 220, 200), 6, 50, 0.3, 2)
            elif kind == "blocked":
                self.fx.burst(x, y, (255, 60, 60), 6, 50, 0.3, 2)
            elif kind == "dash":
                self.fx.burst(x, y, (255, 255, 255), 10, 90, 0.35, 2)
            elif kind == "crash":
                self.fx.burst(x, y, (150, 200, 240), 24, 170, 0.7, 3)
                self.fx.burst(x, y, (70, 160, 80), 6, 90, 0.6, 3)
                self.popup("CLANG!", x, y - 20, (150, 200, 240))
                self.shake = 0.2
            elif kind in ("ward_in", "ward_out"):
                self.fx.burst(x, y + 10, (180, 150, 120), 10, 70, 0.4, 3)
            elif kind == "empty":
                self.popup("Empty!", x, y - 26, (230, 230, 230))
            elif kind == "fish":
                self.fx.burst(x, y, (120, 180, 236), 16, 120, 0.6, 3)
                self.popup("+1", x, y - 16, (150, 210, 255))
            elif kind == "chicken":
                self.fx.burst(x, y, (255, 220, 160), 10, 70, 0.5, 2)
            elif kind == "chomp":
                self.fx.burst(x, y, (206, 128, 56), 14, 90, 0.6, 3)
                self.popup("Yum!", x, y - 20, (255, 200, 120))
            elif kind == "summon_blackcat":
                self.fx.burst(x, y, (90, 70, 120), 26, 150, 0.7, 5)
                self.fx.burst(x, y, (250, 214, 60), 10, 90, 0.5, 2)
            elif kind == "summon_gran":
                self.fx.burst(x, y, (220, 200, 240), 26, 140, 0.7, 5)
                self.fx.burst(x, y, (255, 255, 255), 10, 90, 0.5, 2)
            elif kind == "npc_gone":
                self.fx.burst(x, y, (200, 200, 210), 16, 100, 0.5, 4)
            elif kind == "hold":
                self.fx.burst(x, y, PINK, 16, 110, 0.6, 3)
            elif kind == "hit_fox":
                self.fx.burst(x, y, (232, 52, 72), 24, 170, 0.8, 4)
                self.fx.burst(x, y, (255, 230, 80), 12, 120, 0.6, 3)
                self.popup("-1 сердечко", x, y - 26, (255, 90, 110))
                self.shake = 0.35
            elif kind.startswith("win_"):
                col = FOX_COL if kind == "win_fox" else CAT_COL
                self.fx.burst(x, y, col, 50, 260, 1.2, 5)
                self.fx.burst(x, y, (255, 255, 255), 30, 200, 1.0, 3)
                self.shake = 0.5

    def draw_body(self, b, key, alpha=None):
        frames = self.spr[key][b.facing]
        frame = frames[int(b.anim * 8) % 2] if b.moving else frames[0]
        bob = -abs(int(math.sin(b.anim * 16) * 2)) if b.moving else 0
        x, y = int(b.x), int(b.y) + HUD_H
        sw = max(24, frame.get_width() - 8)
        sh = pygame.Surface((sw, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 80), sh.get_rect())
        self.screen.blit(sh, (x - sw // 2, y + 8))
        if alpha is not None:
            frame = frame.copy()
            frame.set_alpha(alpha)
        r = frame.get_rect(midbottom=(x, y + 12 + bob))
        self.screen.blit(frame, r)
        return r

    def stars(self, x, top):
        for i in range(3):
            a = self.t * 5 + i * math.tau / 3
            self.screen.blit(self.spr["star"], (x + math.cos(a) * 14 - 5, top - 4 + math.sin(a) * 4 - 5))

    def draw_darkness(self, g):
        if g.dark_warning:
            if int(self.t * 12) % 3 == 0:
                o = pygame.Surface((W, H - HUD_H), pygame.SRCALPHA)
                o.fill((5, 5, 15, 150))
                self.screen.blit(o, (0, HUD_H))
            return
        if not g.dark:
            return
        dark = pygame.Surface((W, H - HUD_H), pygame.SRCALPHA)
        base = 238
        dark.fill((5, 5, 15, base))
        lights = [(g.fox, 95)]
        if not g.cat.hidden:
            lights.append((g.cat, 95))
        lights += [(n, 55) for n in g.npcs]
        lights += [(f, 20) for f in g.fish]
        if STYLE["name"] == "manor":
            lights += [(Spot(*cell_center(c, r + 1)), 60) for c, r in FIREPLACES]
        steps = 6
        for i in range(steps):
            a = int(base * (steps - 1 - i) / steps)
            for b, rad in lights:
                r = int(rad * (1 - i / steps * 0.6))
                pygame.draw.circle(dark, (5, 5, 15, a), (int(b.x), int(b.y)), r)
        self.screen.blit(dark, (0, HUD_H))

    def draw_game(self, g, m, dt, state):
        self.t += dt
        self.fx.update(dt)
        self.shake = max(0.0, self.shake - dt)
        scr = self.screen
        scr.fill((20, 16, 24))

        ox = oy = 0
        if self.shake > 0:
            ox, oy = random.randint(-4, 4), random.randint(-4, 4)
        scr.blit(self.bg, (ox, HUD_H + oy))
        for d in g.doors.values():
            draw_door(scr, d, self.t)
        if STYLE["name"] == "manor":
            draw_fire(scr, self.t)
        for s in g.shards:
            draw_shards(scr, s, self.t)
        for v in g.vases:
            if not v.broken:
                x, y = v.center
                scr.blit(self.spr["vase"], self.spr["vase"].get_rect(midbottom=(int(x), int(y) + HUD_H + 4)))
        for i, w in enumerate(g.wardrobes):
            draw_wardrobe(scr, w, i, self.t, g.cat.hidden)

        for f in g.fish:
            img = self.spr["fish"]
            bob = math.sin(self.t * 4 + f.x) * 3
            scr.blit(img, img.get_rect(center=(int(f.x), int(f.y + bob) + HUD_H)))
        if g.chicken:
            x, y = int(g.chicken.x), int(g.chicken.y) + HUD_H
            pygame.draw.ellipse(scr, (120, 120, 130), (x - 14, y - 2, 28, 12))
            pygame.draw.ellipse(scr, (250, 250, 250), (x - 13, y - 3, 26, 10))
            scr.blit(self.spr["chicken"], self.spr["chicken"].get_rect(midbottom=(x, y + 4)))

        # след от рывка лиса
        if g.fox.dash_t > 0:
            self.trail.append([g.fox.x, g.fox.y, 0.25, g.fox.facing])
        for tr in self.trail:
            tr[2] -= dt
        self.trail = [tr for tr in self.trail if tr[2] > 0]
        for x, y, life, facing in self.trail:
            ghost = self.spr["fox"][facing][0].copy()
            ghost.set_alpha(int(life * 400))
            scr.blit(ghost, ghost.get_rect(midbottom=(int(x), int(y) + HUD_H + 12)))

        bodies = [(g.fox, "fox")] + [(n, n.kind) for n in g.npcs]
        if not g.cat.hidden:
            bodies.append((g.cat, "cat"))
        for b, key in sorted(bodies, key=lambda e: e[0].y):
            alpha = None
            if key in ("blackcat", "gran") and b.life < 1.5 and b.holding <= 0:
                alpha = 255 if int(self.t * 10) % 2 else 110
            r = self.draw_body(b, key, alpha)
            if key == "fox":
                if g.fox.stun > 0:
                    self.stars(int(b.x), r.top)
                elif g.fox.eat > 0:
                    scr.blit(self.spr["chicken"], self.spr["chicken"].get_rect(midbottom=(int(b.x), r.top)))
                elif g.fox.boost > 0 and int(self.t * 8) % 2:
                    self.fx.burst(b.x, b.y + 6, (255, 200, 120), 1, 30, 0.4, 2)
            if key == "cat" and g.cat.hold > 0:
                bar(scr, int(b.x) - 16, r.top - 8, 32, 5, g.cat.hold / GRAN_HOLD, PINK)

        if g.cat.hold > 0:
            self.heart_t -= dt
            if self.heart_t <= 0:
                self.heart_t = 0.25
                self.fx.burst(g.cat.x, g.cat.y - 16, PINK, 2, 40, 0.8, 3)

        self.fx.draw(scr)
        self.draw_darkness(g)

        for p in self.popups:
            p[3] -= dt
            p[2] -= 25 * dt
            if p[3] > 0:
                self.text(p[0], self.f_mid, p[4], center=(int(p[1]), int(p[2]) + HUD_H))
        self.popups = [p for p in self.popups if p[3] > 0]

        self.draw_hud(g, m)

        if state == "play" and g.countdown > 0:
            self.overlay(110)
            cat_p, fox_p = m.cat_player, 1 - m.cat_player
            self.text(f"Round {m.round}", self.f_big, (255, 255, 255), center=(W // 2, H // 2 - 110))
            self.text(f"{PLAYER[cat_p]} ({SIDES[cat_p]['names'][0]}) — CAT", self.f_mid, CAT_COL,
                      center=(W // 2, H // 2 - 65))
            self.text(f"{PLAYER[fox_p]} ({SIDES[fox_p]['names'][0]}) — FOX", self.f_mid, FOX_COL,
                      center=(W // 2, H // 2 - 35))
            self.text(str(math.ceil(g.countdown)), self.f_huge, (255, 230, 120), center=(W // 2, H // 2 + 50))
        if g.dark and int(self.t * 2) % 2 and state == "play":
            self.text("LIGHTS OUT!", self.f_mid, (255, 240, 160), center=(W // 2, HUD_H + 20))
        if state == "pause":
            self.overlay()
            self.text("PAUSED", self.f_big, (255, 255, 255), center=(W // 2, H // 2 - 10))
            self.text("P — resume, Esc — menu", self.f_mid, (220, 220, 220), center=(W // 2, H // 2 + 40))
        if state == "over":
            self.draw_round_over(g, m)

    def draw_round_over(self, g, m):
        self.overlay(150)
        msg, col = {
            "caught": ("THE FOX CAUGHT THE CAT!", FOX_COL),
            "wardrobe": ("THE FOX FOUND THE CAT!", FOX_COL),
            "time": ("THE CAT SURVIVED!", CAT_COL),
            "fish": ("THE CAT COLLECTED ALL THE FISH!", CAT_COL),
            "hearts": ("THE BLACK CAT DROVE OFF THE FOX!", CAT_COL),
        }[g.reason]
        cy = H // 2
        self.text(msg, self.f_big, col, center=(W // 2, cy - 70))
        self.text(f"Point goes to {PLAYER[m.last]}", self.f_mid, (230, 230, 230), center=(W // 2, cy - 30))
        self.text(f"{PLAYER[0]}   {m.wins[0]} : {m.wins[1]}   {PLAYER[1]}", self.f_big,
                  (255, 255, 255), center=(W // 2, cy + 20))
        if m.done:
            self.text(f"{PLAYER[m.last].upper()} WON THE MATCH!", self.f_big, (255, 230, 120),
                      center=(W // 2, cy + 75))
            self.text("Enter — new match,  Esc — menu", self.f_small, (210, 210, 210),
                      center=(W // 2, cy + 115))
        else:
            self.text(f"First to {WINS_NEEDED} wins · roles switch next round",
                      self.f_small, (210, 210, 210), center=(W // 2, cy + 65))
            self.text("Enter — следующий раунд,  Esc — меню", self.f_small, (210, 210, 210),
                      center=(W // 2, cy + 92))

    def overlay(self, alpha=120):
        o = pygame.Surface((W, H), pygame.SRCALPHA)
        o.fill((10, 8, 14, alpha))
        self.screen.blit(o, (0, 0))

    def ability(self, x, y, icon, label, key, cd, total, active=False):
        """Значок способности: иконка, подпись с клавишей и полоска перезарядки."""
        self.screen.blit(icon, icon.get_rect(midleft=(x, y + 8)))
        x += icon.get_width() + 5
        if active:
            self.text(f"{label}: идёт!", self.f_tiny, (255, 230, 120), topleft=(x, y + 1))
        elif cd <= 0:
            self.text(f"{label} [{key}]", self.f_tiny, (160, 240, 160), topleft=(x, y + 1))
        else:
            self.text(label, self.f_tiny, (150, 140, 160), topleft=(x, y + 1))
            lw = self.f_tiny.size(label)[0]
            bar(self.screen, x + lw + 5, y + 6, 40, 5, 1 - cd / total, (200, 190, 120))

    def draw_hud(self, g, m):
        scr = self.screen
        pygame.draw.rect(scr, (34, 28, 42), (0, 0, W, HUD_H))
        pygame.draw.line(scr, (80, 66, 96), (0, HUD_H - 1), (W, HUD_H - 1), 2)
        cat_side, fox_side = SIDES[m.cat_player]["names"], SIDES[1 - m.cat_player]["names"]

        # кот
        scr.blit(self.spr["cat_icon"], (10, 8))
        r = self.text(f"CAT · {PLAYER[m.cat_player]}", self.f_mid, CAT_COL, topleft=(44, 6))
        for i in range(FISH_WIN):
            scr.blit(self.fish_icon if i < g.fish_got else self.fish_icon_dim, (r.right + 8 + i * 19, 12))
        if g.cat.hidden:
            self.text(f"in wardrobe {math.ceil(g.cat.hide_t)}s · {cat_side[0]} — move, "
                      f"{cat_side[1]} — exit", self.f_tiny, PINK, topleft=(44, 31))
        elif g.cat.hold > 0:
            self.text("Grandma is holding you!", self.f_tiny, PINK, topleft=(44, 31))
        else:
            self.ability(44, 29, self.spr["blackcat_icon"], "кошка", cat_side[2], g.cat.summon_cd,
                         BLACKCAT_COOLDOWN, active=g.npc("blackcat") is not None)
            if g.cat.ward_cd > 0:
                self.text(f"wardrobe in {math.ceil(g.cat.ward_cd)}s", self.f_tiny, (150, 140, 160),
                          topleft=(200, 31))

        # таймер
        tl = max(0, math.ceil(g.time_left))
        col = (255, 90, 90) if tl <= 10 else (255, 255, 255)
        self.text(f"{tl // 60}:{tl % 60:02d}", self.f_big, col, center=(W // 2 + 30, HUD_H // 2 + 2))

        # лис
        rx = W - 290
        scr.blit(self.spr["fox_icon"], (rx, 8))
        r = self.text(f"FOX · {PLAYER[1 - m.cat_player]}", self.f_mid, FOX_COL, topleft=(rx + 34, 6))
        for i in range(FOX_HEARTS):
            img = self.spr["heart"] if i < g.fox.hearts else self.spr["heart_empty"]
            scr.blit(img, (r.right + 8 + i * 20, 8))
        if g.fox.stun > 0:
            self.text("stunned!", self.f_tiny, (255, 230, 80), topleft=(rx + 34, 31))
        elif g.fox.eat > 0:
            self.text("eating chicken...", self.f_tiny, (255, 200, 120), topleft=(rx + 34, 31))
        else:
            self.ability(rx + 34, 29, self.spr["star"], "рывок", fox_side[1], g.fox.dash_cd, DASH_COOLDOWN)
            self.ability(rx + 146, 29, self.spr["gran_icon"], "бабушка", fox_side[2], g.fox.summon_cd,
                         GRAN_COOLDOWN, active=g.npc("gran") is not None)

    def draw_menu(self, dt):
        self.t += dt
        scr = self.screen
        scr.blit(self.bg, (0, HUD_H))
        self.overlay(185)
        f = int(self.t * 6) % 2

        def show(key, facing, cx, by, scale=1.0):
            img = self.spr[key][facing][f]
            img = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
            scr.blit(img, img.get_rect(midbottom=(cx, by)))

        # название
        title = pygame.font.Font(None, 92)
        bob = math.sin(self.t * 2) * 3
        r = self.text("BLUE BLOOD", title, (120, 160, 255), center=(W // 2, 58 + bob))
        pygame.draw.line(scr, (230, 196, 90), (r.left + 10, r.bottom + 2), (r.right - 10, r.bottom + 2), 2)
        show("blackcat", 1, 62, 104, 1.0)
        show("cat", 1, 150, 100, 1.4)
        show("fox", -1, W - 150, 100, 1.4)
        show("gran", -1, W - 60, 104, 1.1)
        self.text("the cat escapes — the fox hunts · roles switch each round · first to 3 wins",
                  self.f_small, (235, 235, 235), center=(W // 2, 122))

        lx, rx, y0 = 50, W // 2 + 20, 148
        self.text("CAT", self.f_mid, CAT_COL, topleft=(lx, y0))
        for i, s in enumerate(["Survive 1:30 or collect 5 fish",
                               "Action: door / vase / wardrobe",
                               "Break a vase — shards slow the fox",
                               "Hide in a wardrobe and move between",
                               "   wardrobes while the fox guesses",
                               "Perk: black cat — chases the fox",
                               "   and takes one of its hearts"]):
            self.text(s, self.f_small, (235, 235, 235), topleft=(lx, y0 + 28 + i * 22))
        self.text("FOX", self.f_mid, FOX_COL, topleft=(rx, y0))
        for i, s in enumerate(["Catch the cat! You have 3 hearts",
                               "Action: dash",
                               "Wait by a wardrobe to sniff out the cat",
                               "Chicken in the kitchen makes you faster",
                               "Scratch through closed doors",
                               "Perk: grandma — catches the cat",
                               "   and holds it while you run"]):
            self.text(s, self.f_small, (235, 235, 235), topleft=(rx, y0 + 28 + i * 22))

        self.text("Sometimes the lights go out!", self.f_small, (255, 240, 160), center=(W // 2, y0 + 200))
        for i in range(2):
            n = SIDES[i]["names"]
            self.text(f"{PLAYER[i]}:  {n[0]} — move,  {n[1]} — action,  {n[2]} — perk",
                      self.f_small, (200, 220, 255), center=(W // 2, y0 + 236 + i * 24))

        style = "Manor" if STYLE["name"] == "manor" else "House"
        self.text(f"T — оформление: {style}", self.f_small, (190, 190, 200), center=(W // 2, H - 62))
        if int(self.t * 2) % 2 == 0:
            self.text("Press ENTER to start", self.f_mid, (255, 255, 160), center=(W // 2, H - 30))


async def main():
    pygame.init()
    pygame.display.set_caption("Blue Blood")
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()
    rnd = Renderer(screen)
    game = Game()
    match = Match()
    state = "menu"
    held = set()   # физические клавиши, которые сейчас зажаты

    while True:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        keys_down = set()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN:
                keys_down.add(e.scancode)
                held.add(e.scancode)
            elif e.type == pygame.KEYUP:
                held.discard(e.scancode)
            elif e.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
                held.clear()

        if state == "menu":
            if pygame.KSCAN_T in keys_down:
                STYLE["name"] = "classic" if STYLE["name"] == "manor" else "manor"
            if pygame.KSCAN_RETURN in keys_down:
                game, match = Game(), Match()
                rnd.reset()
                state = "play"
            rnd.draw_menu(dt)
        elif state == "play":
            if pygame.KSCAN_P in keys_down or pygame.KSCAN_ESCAPE in keys_down:
                state = "pause"
            else:
                game.step(dt, match.inputs(held, keys_down))
                rnd.handle_events(game)
                if game.winner:
                    match.finish_round(game.winner)
                    state = "over"
            rnd.draw_game(game, match, dt, state)
        elif state == "pause":
            if pygame.KSCAN_P in keys_down:
                state = "play"
            elif pygame.KSCAN_ESCAPE in keys_down:
                state = "menu"
            rnd.draw_game(game, match, 0, state)
        elif state == "over":
            if pygame.KSCAN_RETURN in keys_down:
                if match.done:
                    match = Match()
                else:
                    match.next_round()
                game.new_round()
                rnd.reset()
                state = "play"
            elif pygame.KSCAN_ESCAPE in keys_down:
                state = "menu"
            rnd.draw_game(game, match, dt, state)

        pygame.display.flip()
        await asyncio.sleep(0)  # нужно для работы в браузере (pygbag)


if __name__ == "__main__":
    asyncio.run(main())
