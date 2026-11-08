"""A classic 18th-19th century English country house in neutral tones, drawn in code.

Every location (level) shares the same drawing code; the per-level details
(wall decorations, rugs, chandeliers) are listed at the top.
"""
import math
import random

import pygame

import logic
from logic import COLS, ROWS, TILE

GOLD = (186, 158, 102)          # soft, muted gilt
GOLD_D = (140, 116, 72)
WALL = (84, 74, 68)             # top of the walls
WALL_D = (74, 65, 60)
DOOR_C = (128, 92, 62)          # warm oak doors
DOOR_D = (86, 60, 40)
FACE_H = 18                     # height of the visible wall face

WOOD = (132, 96, 66)
WOOD_D = (92, 64, 44)
MARBLE = (232, 228, 220)
CREAM = (228, 216, 192)
SAGE = (146, 156, 126)
BLUE = (132, 148, 162)
ROSE = (180, 136, 128)

# wall colour per room (neutral paints and papers)
WALLPAPER = {
    "drawing": (178, 184, 158), "library": (150, 124, 98), "hall": (224, 214, 194),
    "dining": (176, 188, 186), "study": (156, 144, 116),
    "master": (210, 188, 174), "boudoir": (198, 188, 196), "guest": (224, 212, 172),
    "gallery": (226, 218, 200), "nursery": (192, 206, 186), "bath": (228, 228, 224),
    "landing": (224, 214, 194), "guest2": (188, 198, 206),
    "kitchen": (210, 204, 190), "scullery": (210, 204, 190), "larder": (206, 200, 186),
    "butler": (196, 186, 166), "cellar": (150, 144, 134), "passage": (214, 208, 194),
    "servants": (214, 208, 194), "laundry": (218, 214, 204), "housekeeper": (200, 190, 170),
    "palmhouse": (196, 220, 220), "fountain": (196, 220, 220), "orchid": (196, 220, 220),
    "rosegarden": (196, 220, 220), "tearoom": (196, 220, 220), "potting": (196, 210, 200),
}
TILED_WALLS = {"kitchen", "scullery", "larder", "bath", "laundry"}
STONE_WALLS = {"cellar"}

DECOR = {  # level -> {(col, wall row): kind}
    "ground": {
        (3, 0): "window", (6, 0): "fireplace", (10, 0): "window",
        (16, 0): "sconce", (23, 0): "sconce", (24, 0): "portrait",
        (30, 0): "portrait", (32, 0): "fireplace", (35, 0): "portrait",
        (33, 10): "portrait", (31, 10): "sconce",
    },
    "upper": {
        (3, 0): "window", (10, 0): "fireplace", (17, 0): "mirror", (21, 0): "window",
        (27, 0): "portrait", (34, 0): "window", (36, 0): "fireplace",
        (3, 8): "portrait", (9, 8): "portrait", (14, 8): "sconce", (16, 8): "portrait",
        (23, 8): "portrait", (25, 8): "sconce", (27, 8): "portrait", (36, 8): "portrait",
        (3, 12): "window", (8, 12): "portrait", (16, 12): "mirror", (29, 12): "portrait", (36, 12): "window",
    },
    "service": {
        (3, 0): "window", (10, 0): "window", (19, 0): "window", (26, 0): "portrait",
        (8, 10): "lamp", (17, 10): "lamp", (24, 10): "lamp", (31, 10): "lamp",
        (11, 13): "fireplace", (22, 13): "window", (35, 13): "portrait",
    },
    "garden": {
        (4, 0): "lamp", (10, 0): "lamp", (19, 0): "lamp", (21, 0): "lamp", (31, 0): "lamp", (35, 0): "lamp",
        (3, 10): "lamp", (12, 10): "lamp", (23, 10): "lamp", (26, 10): "lamp", (36, 10): "lamp",
    },
}
RUGS = {  # level -> [(col, row, w, h, base, border)]
    "ground": [(2, 2, 9, 6, (156, 126, 100), (112, 88, 70)), (28, 3, 10, 4, (140, 120, 104), (98, 80, 66)),
               (28, 13, 8, 5, (150, 112, 96), (106, 78, 66))],
    "upper": [(4, 4, 6, 3, (176, 150, 140), (130, 104, 96)), (27, 4, 7, 3, (150, 158, 130), (108, 116, 92)),
              (27, 14, 7, 3, (140, 152, 166), (100, 110, 124)), (3, 15, 5, 4, (200, 196, 170), (150, 146, 120))],
    "service": [],
    "garden": [(20, 14, 8, 3, (176, 150, 120), (130, 106, 84))],
}
RUNNERS = {  # level -> [(col, row, w, h)] long carpet runners
    "ground": [(19, 4, 2, 16)],
    "upper": [(1, 10, 38, 1)],
    "service": [],
    "garden": [],
}
CHANDELIERS = {"ground": [(20, 7), (20, 15)], "upper": [(10, 10), (20, 10), (30, 10)], "service": [],
               "garden": [(20, 5), (7, 5), (24, 15)]}


def level():
    return logic.LEVEL["name"]


def fireplaces():
    return [c for c, k in DECOR[level()].items() if k == "fireplace"]


def shade(col, d):
    return tuple(max(0, min(255, v + d)) for v in col)


# --- floors ----------------------------------------------------------------
def _herringbone(surf, x, y, c, r, light, dark):
    pygame.draw.rect(surf, light, (x, y, TILE, TILE))
    for i in range(4):
        for j in range(2):
            bx, by = x + i * 8, y + j * 16
            if (i + j + c + r) % 2 == 0:
                pygame.draw.line(surf, dark, (bx, by), (bx + 8, by + 8))
                pygame.draw.line(surf, dark, (bx, by + 8), (bx + 8, by + 16))
            else:
                pygame.draw.line(surf, dark, (bx + 8, by), (bx, by + 8))
                pygame.draw.line(surf, dark, (bx + 8, by + 8), (bx, by + 16))
    rnd = random.Random(c * 31 + r * 17)
    if rnd.random() < 0.3:
        pygame.draw.rect(surf, shade(light, 8), (x + rnd.randint(2, 24), y + rnd.randint(2, 24), 4, 2))


def _planks(surf, x, y, c, r, light, dark):
    rnd = random.Random(c * 97 + r * 31)
    pygame.draw.rect(surf, light, (x, y, TILE, TILE))
    for k in range(4):
        yy = y + k * 8
        pygame.draw.line(surf, dark, (x, yy), (x + TILE, yy))
        off = rnd.randint(0, TILE)
        pygame.draw.line(surf, dark, (x + off, yy), (x + off, yy + 8))


def _carpet(surf, x, y, base):
    pygame.draw.rect(surf, base, (x, y, TILE, TILE))
    dot = shade(base, 12)
    for i in range(4):
        for j in range(4):
            if (i + j) % 2 == 0:
                pygame.draw.rect(surf, dot, (x + i * 8 + 3, y + j * 8 + 3, 2, 2))


def _flags(surf, x, y, c, r, base, joint, size=16):
    rnd = random.Random(c * 13 + r * 7)
    for i in range(TILE // size):
        for j in range(TILE // size):
            pygame.draw.rect(surf, shade(base, rnd.randint(-6, 6)), (x + i * size, y + j * size, size, size))
            pygame.draw.rect(surf, joint, (x + i * size, y + j * size, size, size), 1)


FLOOR = {
    "drawing": ("herring", (204, 170, 126), (180, 146, 104)),
    "dining": ("herring", (196, 160, 116), (172, 136, 96)),
    "study": ("herring", (172, 132, 92), (148, 110, 74)),
    "gallery": ("herring", (204, 170, 126), (180, 146, 104)),
    "landing": ("herring", (204, 170, 126), (180, 146, 104)),
    "library": ("herring", (150, 112, 78), (126, 92, 62)),
    "hall": ("stone", (220, 210, 190), (196, 186, 166), 32),
    "bath": ("stone", (232, 232, 228), (206, 206, 202), 16),
    "kitchen": ("stone", (184, 176, 160), (154, 146, 132), 16),
    "scullery": ("stone", (184, 176, 160), (154, 146, 132), 16),
    "larder": ("stone", (184, 176, 160), (154, 146, 132), 16),
    "cellar": ("stone", (140, 132, 122), (112, 106, 98), 16),
    "master": ("carpet", (184, 158, 146)), "boudoir": ("carpet", (176, 160, 162)),
    "guest": ("carpet", (158, 166, 138)), "guest2": ("carpet", (150, 160, 172)),
    "nursery": ("carpet", (204, 206, 182)),
    "palmhouse": ("stone", (200, 194, 172), (172, 170, 146), 16),
    "fountain": ("stone", (216, 208, 188), (190, 182, 162), 32),
    "orchid": ("terra", (190, 132, 100), (164, 110, 82)),
    "rosegarden": ("grass", (122, 150, 98), (104, 132, 82)),
    "tearoom": ("herring", (210, 178, 134), (186, 154, 112)),
    "potting": ("brick", (168, 112, 88), (140, 92, 72)),
}


def draw_floor(surf, c, r):
    x, y = c * TILE, r * TILE
    kind = FLOOR.get(logic.room_of(c, r), ("planks", (184, 154, 114), (160, 130, 94)))
    if kind[0] == "herring":
        _herringbone(surf, x, y, c, r, kind[1], kind[2])
    elif kind[0] == "stone":
        _flags(surf, x, y, c, r, kind[1], kind[2], kind[3])
    elif kind[0] == "carpet":
        _carpet(surf, x, y, kind[1])
    elif kind[0] == "terra":
        for i in range(2):
            for j in range(2):
                col = kind[1] if (i + j + c + r) % 2 == 0 else shade(kind[1], -8)
                pygame.draw.rect(surf, col, (x + i * 16, y + j * 16, 16, 16))
                pygame.draw.rect(surf, kind[2], (x + i * 16, y + j * 16, 16, 16), 1)
    elif kind[0] == "grass":
        pygame.draw.rect(surf, kind[1], (x, y, TILE, TILE))
        rnd = random.Random(c * 41 + r * 3)
        for _ in range(10):
            gx, gy = x + rnd.randint(1, 30), y + rnd.randint(2, 30)
            pygame.draw.line(surf, rnd.choice([kind[2], shade(kind[1], 14)]), (gx, gy), (gx + rnd.randint(-1, 1), gy - 3))
    elif kind[0] == "brick":
        pygame.draw.rect(surf, kind[1], (x, y, TILE, TILE))
        for k in range(0, TILE, 8):
            off = 8 if (k // 8 + r) % 2 else 0
            pygame.draw.line(surf, kind[2], (x, y + k), (x + TILE, y + k))
            for bx in range(off, TILE, 16):
                pygame.draw.line(surf, kind[2], (x + bx, y + k), (x + bx, y + k + 8))
    else:
        _planks(surf, x, y, c, r, kind[1], kind[2])


def draw_rug(surf, rect, base, border):
    pygame.draw.rect(surf, border, rect)
    inner = rect.inflate(-10, -10)
    pygame.draw.rect(surf, base, inner)
    pygame.draw.rect(surf, CREAM, inner.inflate(-6, -6), 1)
    cx, cy = inner.center
    s = min(inner.w, inner.h) // 3
    pygame.draw.polygon(surf, shade(border, 30), [(cx, cy - s), (cx + s * 1.4, cy), (cx, cy + s), (cx - s * 1.4, cy)], 2)
    for k in range(rect.x + 2, rect.right - 2, 4):
        pygame.draw.line(surf, CREAM, (k, rect.y - 3), (k, rect.y))
        pygame.draw.line(surf, CREAM, (k, rect.bottom), (k, rect.bottom + 3))


# --- walls -----------------------------------------------------------------
def _glass_wall(surf, c, r):
    """Conservatory walls: white iron frames with glass panes."""
    x, y = c * TILE, r * TILE
    pygame.draw.rect(surf, (184, 210, 212), (x, y, TILE, TILE))
    for k in range(0, TILE + 1, 8):
        pygame.draw.line(surf, (238, 238, 232), (x + k, y), (x + k, y + TILE))
    pygame.draw.line(surf, (238, 238, 232), (x, y + 16), (x + TILE, y + 16), 2)
    pygame.draw.line(surf, (226, 240, 242), (x + 2, y + 6), (x + 6, y + 2))
    pygame.draw.line(surf, (226, 240, 242), (x + 18, y + 22), (x + 22, y + 18))
    kind = DECOR[level()].get((c, r))
    if kind == "lamp" and r + 1 < ROWS and logic.MAP[r + 1][c] != "#":
        pygame.draw.line(surf, (70, 66, 60), (x + 16, y + 10), (x + 16, y + 18))
        pygame.draw.rect(surf, (60, 56, 52), (x + 11, y + 18, 10, 10))
        pygame.draw.rect(surf, (255, 222, 140), (x + 13, y + 20, 6, 6))


def draw_wall(surf, c, r):
    x, y = c * TILE, r * TILE
    M = logic.MAP
    if level() == "garden":
        _glass_wall(surf, c, r)
        return
    pygame.draw.rect(surf, WALL, (x, y, TILE, TILE))
    for k in range(0, TILE, 8):
        pygame.draw.line(surf, WALL_D, (x, y + k), (x + TILE, y + k))
    if (c, r) in logic.LEVEL["front_door"]:
        _front_door(surf, c, r)
        return
    if r + 1 >= ROWS or M[r + 1][c] == "#":
        return
    room = logic.room_of(c, r + 1)
    paper = WALLPAPER.get(room, CREAM)
    fy = y + TILE - FACE_H
    pygame.draw.rect(surf, paper, (x, fy, TILE, FACE_H))
    if room in TILED_WALLS:
        for k in range(0, TILE, 8):
            pygame.draw.line(surf, shade(paper, -16), (x + k, fy), (x + k, y + TILE - 4))
        pygame.draw.line(surf, shade(paper, -16), (x, fy + 8), (x + TILE, fy + 8))
    elif room in STONE_WALLS:
        for k in range(0, FACE_H, 6):
            off = 8 if (k // 6 + c) % 2 else 0
            pygame.draw.line(surf, shade(paper, -20), (x, fy + k), (x + TILE, fy + k))
            pygame.draw.line(surf, shade(paper, -20), (x + off + 4, fy + k), (x + off + 4, fy + k + 6))
    else:  # painted wall over wood panelling
        pygame.draw.rect(surf, shade(paper, -34), (x, fy + 10, TILE, FACE_H - 10))
        pygame.draw.rect(surf, shade(paper, -50), (x + 3, fy + 11, 11, 4), 1)
        pygame.draw.rect(surf, shade(paper, -50), (x + 18, fy + 11, 11, 4), 1)
        for k in range(4, TILE, 8):
            pygame.draw.line(surf, shade(paper, -8), (x + k, fy + 1), (x + k, fy + 9))
    pygame.draw.line(surf, shade(paper, 24), (x, fy), (x + TILE, fy))       # cornice
    pygame.draw.rect(surf, (112, 90, 70), (x, y + TILE - 3, TILE, 3))      # skirting
    kind = DECOR[level()].get((c, r))
    if kind == "portrait":
        rnd = random.Random(c * 7 + r)
        fr = pygame.Rect(x + 8, fy - 7, 16, 20)
        pygame.draw.rect(surf, GOLD, fr)
        pygame.draw.rect(surf, GOLD_D, fr, 1)
        inner = fr.inflate(-4, -4)
        pygame.draw.rect(surf, rnd.choice([(84, 92, 96), (110, 96, 80), (96, 104, 86)]), inner)
        pygame.draw.ellipse(surf, rnd.choice([(96, 72, 54), (210, 208, 212), (150, 116, 70), (60, 50, 44)]),
                            (inner.x + 2, inner.y + 1, inner.w - 4, 8))
        pygame.draw.ellipse(surf, (226, 198, 172), (inner.x + 4, inner.y + 3, inner.w - 8, 7))
        pygame.draw.rect(surf, rnd.choice([(60, 60, 70), (120, 80, 70), (70, 84, 110), (90, 100, 80)]),
                         (inner.x + 1, inner.y + 10, inner.w - 2, inner.h - 10))
    elif kind == "sconce":
        pygame.draw.rect(surf, GOLD, (x + 12, fy + 6, 8, 3))
        for dx in (13, 18):
            pygame.draw.rect(surf, (246, 242, 228), (x + dx, fy + 1, 2, 5))
            pygame.draw.circle(surf, (255, 214, 120), (x + dx + 1, fy), 2)
    elif kind == "lamp":
        pygame.draw.line(surf, (60, 56, 52), (x + 16, fy - 2), (x + 16, fy + 4))
        pygame.draw.rect(surf, (70, 66, 60), (x + 12, fy + 4, 8, 7))
        pygame.draw.rect(surf, (255, 220, 140), (x + 14, fy + 6, 4, 4))
    elif kind == "window":
        fr = pygame.Rect(x + 6, fy - 9, 20, 23)
        pygame.draw.rect(surf, (236, 232, 222), fr)
        pygame.draw.rect(surf, (164, 196, 214), fr.inflate(-4, -4))
        pygame.draw.line(surf, (236, 232, 222), (fr.centerx, fr.y), (fr.centerx, fr.bottom))
        pygame.draw.line(surf, (236, 232, 222), (fr.x, fr.centery), (fr.right, fr.centery))
        pygame.draw.rect(surf, (196, 180, 150), (x + 2, fy - 10, 5, 25))   # linen curtains
        pygame.draw.rect(surf, (196, 180, 150), (x + 25, fy - 10, 5, 25))
        pygame.draw.line(surf, GOLD_D, (x + 1, fy - 11), (x + 31, fy - 11), 2)
    elif kind == "mirror":
        fr = pygame.Rect(x + 7, fy - 8, 18, 21)
        pygame.draw.ellipse(surf, GOLD, fr)
        pygame.draw.ellipse(surf, (206, 216, 224), fr.inflate(-5, -5))
        pygame.draw.line(surf, (240, 246, 250), (fr.x + 7, fr.y + 6), (fr.x + 10, fr.y + 3), 2)
    elif kind == "fireplace":
        pygame.draw.rect(surf, (222, 214, 198), (x - 1, y + 6, 34, TILE - 6))      # pale stone mantel
        pygame.draw.rect(surf, (192, 184, 168), (x - 1, y + 6, 34, TILE - 6), 1)
        pygame.draw.rect(surf, (236, 230, 216), (x - 3, y + 4, 38, 4))
        pygame.draw.rect(surf, (30, 24, 22), (x + 8, y + 14, 16, TILE - 14))
        pygame.draw.rect(surf, GOLD_D, (x + 7, y + 13, 18, 2))
        pygame.draw.circle(surf, (246, 240, 226), (x + 3, y + 1), 2)
        pygame.draw.circle(surf, (246, 240, 226), (x + 29, y + 1), 2)


def _front_door(surf, c, r):
    """The grand front door, set into the outer wall."""
    x, y = c * TILE, r * TILE
    left = (c - 1, r) not in logic.LEVEL["front_door"]
    pygame.draw.rect(surf, (222, 214, 198), (x, y, TILE, TILE))                  # stone surround
    leaf = pygame.Rect(x + (4 if left else 0), y + 3, TILE - 4, TILE - 3)
    pygame.draw.rect(surf, DOOR_D, leaf)
    pygame.draw.rect(surf, DOOR_C, leaf.inflate(-4, -4))
    pygame.draw.rect(surf, DOOR_D, leaf.inflate(-12, -14), 1)
    pygame.draw.circle(surf, GOLD, (leaf.right - 4 if left else leaf.x + 4, leaf.centery), 2)


# --- furniture -------------------------------------------------------------
def _block(c, r, ch):
    """Size of a rectangular furniture block, or None if (c, r) isn't its top-left corner."""
    M = logic.MAP
    if (c > 0 and M[r][c - 1] == ch) or (r > 0 and M[r - 1][c] == ch):
        return None
    w = h = 0
    while c + w < COLS and M[r][c + w] == ch:
        w += 1
    while r + h < ROWS and M[r + h][c] == ch:
        h += 1
    return w, h


def _shadow(surf, rect, r=4):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, 50), s.get_rect(), border_radius=r)
    surf.blit(s, rect.move(0, 3))


def draw_furniture(surf, c, r, ch):
    M = logic.MAP
    x, y = c * TILE, r * TILE
    room = logic.room_of(c, r)
    if ch in "tTBdsPSbhLkoRuHn":
        size = _block(c, r, ch)
        if size is None:
            return
        bw, bh = size
        rect = pygame.Rect(x, y, bw * TILE, bh * TILE)
    if ch == "k":                                           # counters, cupboards, washstands
        _shadow(surf, rect.inflate(-2, -2))
        pygame.draw.rect(surf, (196, 186, 166), rect.inflate(-2, -2).move(0, 4))
        pygame.draw.rect(surf, (226, 222, 212), (rect.x + 1, rect.y, rect.w - 2, 10))
        pygame.draw.line(surf, (190, 186, 176), (rect.x, rect.y + 10), (rect.right, rect.y + 10))
        for k in range(bw):
            px = rect.x + k * TILE
            pygame.draw.rect(surf, (166, 154, 132), (px + 4, rect.y + 14, 24, 13), 1)
            pygame.draw.circle(surf, GOLD_D, (px + 16, rect.y + 20), 1)
        if room == "bath":
            pygame.draw.ellipse(surf, (244, 244, 246), (rect.x + 6, rect.y + 1, 20, 8))
    elif ch == "o":                                         # cast-iron kitchen range
        _shadow(surf, rect)
        pygame.draw.rect(surf, (52, 50, 54), rect.inflate(-2, -4))
        pygame.draw.rect(surf, (84, 82, 88), (rect.x + 3, rect.y + 3, rect.w - 6, 9))
        for k in range(bw):
            pygame.draw.circle(surf, (130, 128, 136), (rect.x + k * TILE + 16, rect.y + 7), 3, 1)
        pygame.draw.line(surf, GOLD, (rect.x + 3, rect.y + 15), (rect.right - 4, rect.y + 15), 2)
        pygame.draw.rect(surf, (210, 110, 50), (rect.centerx - 8, rect.y + 20, 16, 6))
    elif ch == "t":                                         # plain wooden table
        _shadow(surf, rect.inflate(-4, -4))
        pygame.draw.rect(surf, WOOD_D, rect.inflate(-4, -4).move(0, 2))
        pygame.draw.rect(surf, (176, 136, 94), rect.inflate(-4, -6))
        pygame.draw.rect(surf, WOOD, rect.inflate(-4, -6), 1)
        pygame.draw.ellipse(surf, CREAM, (rect.centerx - 7, rect.centery - 4, 14, 8))
    elif ch == "T":                                         # long dining table
        tab = rect.inflate(-4, -4)
        _shadow(surf, tab)
        pygame.draw.rect(surf, WOOD_D, tab.move(0, 2), border_radius=3)
        pygame.draw.rect(surf, (238, 234, 224), tab, border_radius=3)              # linen cloth
        pygame.draw.line(surf, (214, 208, 196), (tab.x, tab.bottom - 3), (tab.right, tab.bottom - 3))
        for k in range(bw):
            px = x + k * TILE + 16
            for py in (tab.y + 7, tab.bottom - 7):
                pygame.draw.circle(surf, (250, 250, 250), (px, py), 5)
                pygame.draw.circle(surf, (190, 196, 206), (px, py), 5, 1)
        for cx in (tab.x + tab.w // 4, tab.right - tab.w // 4):
            pygame.draw.rect(surf, GOLD, (cx - 6, tab.centery - 1, 12, 3))
            for dx in (-5, 0, 5):
                pygame.draw.rect(surf, (250, 248, 238), (cx + dx - 1, tab.centery - 8, 2, 7))
                pygame.draw.circle(surf, (255, 206, 100), (cx + dx, tab.centery - 9), 2)
        pygame.draw.circle(surf, SAGE, tab.center, 5)                              # flowers
        pygame.draw.circle(surf, ROSE, (tab.centerx - 2, tab.centery - 1), 2)
        pygame.draw.circle(surf, CREAM, (tab.centerx + 2, tab.centery + 1), 2)
    elif ch == "f":                                         # sideboard / nightstand
        _shadow(surf, pygame.Rect(x + 3, y + 5, 26, 23))
        pygame.draw.rect(surf, WOOD_D, (x + 3, y + 7, 26, 22), border_radius=2)
        pygame.draw.rect(surf, WOOD, (x + 3, y + 5, 26, 21), border_radius=2)
        pygame.draw.line(surf, WOOD_D, (x + 4, y + 15), (x + 27, y + 15))
        pygame.draw.circle(surf, GOLD, (x + 16, y + 20), 1)
        pygame.draw.circle(surf, CREAM, (x + 16, y + 9), 3)                         # lamp / bowl
    elif ch == "L":                                         # shelves: books, silver or wine
        rnd = random.Random(c * 5 + r)
        sh = pygame.Rect(rect.x + 1, rect.y - 8, rect.w - 2, rect.h + 6)
        pygame.draw.rect(surf, (104, 74, 50), sh)
        rows = max(3, sh.h // 11)
        for row in range(rows - 1):
            yy = sh.y + 3 + row * 11
            xx = sh.x + 3
            while xx < sh.right - 4:
                if room == "cellar":
                    pygame.draw.circle(surf, rnd.choice([(70, 30, 40), (50, 70, 40), (90, 60, 30)]), (xx + 2, yy + 6), 2)
                    xx += 5
                    continue
                if room in ("butler", "larder", "housekeeper"):
                    col = rnd.choice([(210, 210, 216), (230, 226, 214), (186, 160, 110)])
                else:
                    col = rnd.choice([(124, 70, 58), (84, 96, 118), (96, 112, 84), (176, 150, 96), (140, 120, 100)])
                w = rnd.randint(2, 4)
                h = rnd.randint(6, 9)
                pygame.draw.rect(surf, col, (xx, yy + 9 - h, w, h))
                xx += w + 1
            pygame.draw.line(surf, (130, 96, 66), (sh.x, yy + 9), (sh.right - 1, yy + 9), 2)
    elif ch == "B":                                         # billiard table
        _shadow(surf, rect)
        pygame.draw.rect(surf, WOOD_D, rect.inflate(-2, -2), border_radius=4)
        felt = rect.inflate(-12, -12)
        pygame.draw.rect(surf, (70, 120, 84), felt)
    elif ch == "d":                                         # writing desk
        _shadow(surf, rect.inflate(-2, -2))
        pygame.draw.rect(surf, WOOD_D, rect.inflate(-2, -2).move(0, 2))
        pygame.draw.rect(surf, WOOD, rect.inflate(-2, -4))
        pygame.draw.rect(surf, (96, 116, 90), rect.inflate(-14, -14))
        pygame.draw.rect(surf, (244, 238, 222), (rect.x + 10, rect.y + 10, 10, 8))
        pygame.draw.rect(surf, GOLD, (rect.right - 16, rect.y + 6, 4, 10))
        pygame.draw.circle(surf, (236, 220, 170), (rect.right - 14, rect.y + 6), 4)
    elif ch == "s":                                         # sofa / chaise longue
        col = {"boudoir": ROSE, "study": (150, 120, 96)}.get(room, SAGE)
        sofa = rect.inflate(-2, -4)
        _shadow(surf, sofa, 7)
        pygame.draw.rect(surf, shade(col, -40), sofa.move(0, 2), border_radius=7)
        pygame.draw.rect(surf, col, sofa, border_radius=7)
        pygame.draw.rect(surf, shade(col, -20), (sofa.x, sofa.y, sofa.w, 9), border_radius=7)
        for k in range(sofa.x + 6, sofa.right - 4, 10):
            pygame.draw.circle(surf, shade(col, -34), (k, sofa.y + 15), 1)
    elif ch == "a":                                         # armchair
        col = {"boudoir": ROSE, "master": ROSE, "study": (150, 120, 96), "guest2": BLUE,
               "housekeeper": (150, 130, 110)}.get(room, SAGE)
        _shadow(surf, pygame.Rect(x + 4, y + 3, 24, 25), 6)
        pygame.draw.rect(surf, shade(col, -40), (x + 4, y + 5, 24, 24), border_radius=6)
        pygame.draw.rect(surf, col, (x + 5, y + 3, 22, 23), border_radius=6)
        pygame.draw.rect(surf, shade(col, -18), (x + 5, y + 3, 22, 8), border_radius=6)
        pygame.draw.rect(surf, shade(col, 16), (x + 9, y + 12, 14, 10), border_radius=3)
        pygame.draw.rect(surf, WOOD_D, (x + 6, y + 27, 3, 3))
        pygame.draw.rect(surf, WOOD_D, (x + 23, y + 27, 3, 3))
    elif ch == "P":                                         # grand piano
        body = rect.inflate(-4, -4)
        _shadow(surf, body, 12)
        pygame.draw.ellipse(surf, (40, 34, 30), body)
        pygame.draw.ellipse(surf, (70, 60, 54), body.inflate(-16, -16), 1)
        keys = pygame.Rect(body.x + 4, body.bottom - 12, body.w - 8, 8)
        pygame.draw.rect(surf, (244, 242, 236), keys)
        for k in range(keys.x + 3, keys.right, 4):
            pygame.draw.line(surf, (30, 30, 30), (k, keys.y), (k, keys.y + 4))
    elif ch == "I":                                         # marble column
        pygame.draw.rect(surf, (200, 194, 182), (x + 3, y + 3, 26, 26))
        pygame.draw.rect(surf, (176, 170, 158), (x + 3, y + 3, 26, 26), 1)
        pygame.draw.circle(surf, (190, 184, 172), (x + 16, y + 16), 11)
        pygame.draw.circle(surf, MARBLE, (x + 16, y + 16), 10)
        pygame.draw.circle(surf, (246, 244, 238), (x + 13, y + 12), 4)
    elif ch == "R":                                         # round hall table with flowers
        _shadow(surf, rect.inflate(-6, -6), 30)
        pygame.draw.ellipse(surf, WOOD_D, rect.inflate(-6, -4).move(0, 2))
        pygame.draw.ellipse(surf, (176, 136, 94), rect.inflate(-6, -6))
        pygame.draw.ellipse(surf, WOOD, rect.inflate(-6, -6), 2)
        cx, cy = rect.center
        pygame.draw.circle(surf, MARBLE, (cx, cy + 4), 7)
        for dx, dy, col in ((-6, -4, SAGE), (5, -6, SAGE), (0, -10, (100, 130, 90)), (-3, -6, CREAM),
                            (4, -2, ROSE), (-7, 1, (240, 236, 220)), (7, 2, ROSE), (0, -3, (230, 200, 150))):
            pygame.draw.circle(surf, col, (cx + dx, cy + dy), 4)
    elif ch == "b":                                         # bed against the wall
        bed = rect.inflate(-4, -4)
        _shadow(surf, bed)
        head_top = r > 0 and M[r - 1][c] == "#"
        cover = {"master": (196, 170, 156), "guest": (170, 178, 146), "guest2": (160, 172, 186),
                 "nursery": (210, 200, 170)}.get(room, CREAM)
        pygame.draw.rect(surf, WOOD_D, bed)
        pygame.draw.rect(surf, (244, 240, 230), bed.inflate(-6, -6))
        if head_top:
            pygame.draw.rect(surf, WOOD, (bed.x, bed.y, bed.w, 6))
            pil = bed.y + 8
            blanket = pygame.Rect(bed.x + 3, bed.y + 24, bed.w - 6, bed.h - 27)
        else:
            pygame.draw.rect(surf, WOOD, (bed.x, bed.bottom - 6, bed.w, 6))
            pil = bed.bottom - 22
            blanket = pygame.Rect(bed.x + 3, bed.y + 3, bed.w - 6, bed.h - 27)
        pygame.draw.rect(surf, cover, blanket)
        pygame.draw.rect(surf, shade(cover, -24), blanket, 1)
        pygame.draw.line(surf, shade(cover, 24), (blanket.x, blanket.y + 6), (blanket.right - 1, blanket.y + 6))
        n = 2 if bed.w > 50 else 1
        pw = (bed.w - 12) // n - 4
        for k in range(n):
            pygame.draw.rect(surf, (252, 252, 250), (bed.x + 6 + k * (pw + 4), pil, pw, 12), border_radius=4)
    elif ch == "h":                                         # bathtub / wash tub
        tub = rect.inflate(-4, -4)
        _shadow(surf, tub, 10)
        pygame.draw.rect(surf, (230, 230, 232), tub, border_radius=10)
        pygame.draw.rect(surf, (200, 200, 206), tub, 1, border_radius=10)
        pygame.draw.rect(surf, (176, 206, 220), tub.inflate(-8, -8), border_radius=8)
        if room == "bath":
            for px, py in (tub.topleft, tub.topright, tub.bottomleft, tub.bottomright):
                pygame.draw.circle(surf, GOLD, (px, py), 2)
    elif ch == "e":                                         # dressing table with a mirror
        _shadow(surf, pygame.Rect(x + 2, y + 8, 28, 20))
        pygame.draw.rect(surf, WOOD, (x + 2, y + 10, 28, 18), border_radius=2)
        pygame.draw.ellipse(surf, GOLD, (x + 8, y - 4, 16, 16))
        pygame.draw.ellipse(surf, (206, 216, 224), (x + 10, y - 2, 12, 12))
        pygame.draw.circle(surf, ROSE, (x + 6, y + 15), 2)
        pygame.draw.circle(surf, CREAM, (x + 26, y + 15), 2)
    elif ch == "y":                                         # rocking horse
        pygame.draw.arc(surf, WOOD_D, (x + 3, y + 18, 26, 12), math.pi, 2 * math.pi, 3)
        pygame.draw.rect(surf, (236, 228, 214), (x + 8, y + 10, 16, 9), border_radius=4)
        pygame.draw.rect(surf, (236, 228, 214), (x + 21, y + 4, 6, 9), border_radius=2)
        pygame.draw.line(surf, (150, 110, 80), (x + 22, y + 4), (x + 18, y + 12), 2)
        pygame.draw.rect(surf, ROSE, (x + 12, y + 9, 6, 3))
    elif ch == "g":                                         # barrel
        _shadow(surf, pygame.Rect(x + 4, y + 4, 24, 24), 12)
        pygame.draw.circle(surf, (120, 82, 54), (x + 16, y + 16), 12)
        pygame.draw.circle(surf, (150, 108, 72), (x + 16, y + 16), 10)
        pygame.draw.circle(surf, (80, 76, 72), (x + 16, y + 16), 12, 2)
        pygame.draw.circle(surf, (80, 76, 72), (x + 16, y + 16), 6, 1)
    elif ch == "x":                                         # marble bust on a plinth
        pygame.draw.rect(surf, (200, 194, 182), (x + 7, y + 14, 18, 16))
        pygame.draw.rect(surf, (176, 170, 158), (x + 7, y + 14, 18, 16), 1)
        pygame.draw.ellipse(surf, MARBLE, (x + 8, y + 8, 16, 9))
        pygame.draw.circle(surf, MARBLE, (x + 16, y + 4), 6)
        pygame.draw.circle(surf, (210, 206, 198), (x + 18, y + 4), 6, 1)
    elif ch == "c":                                         # grandfather clock
        body = pygame.Rect(x + 8, y - 14, 16, 44)
        pygame.draw.rect(surf, WOOD_D, body)
        pygame.draw.rect(surf, WOOD, body.inflate(-2, -2))
        pygame.draw.circle(surf, (244, 238, 220), (body.centerx, body.y + 8), 6)
        pygame.draw.circle(surf, GOLD, (body.centerx, body.y + 8), 6, 1)
        pygame.draw.line(surf, (30, 30, 30), (body.centerx, body.y + 8), (body.centerx, body.y + 4))
        pygame.draw.line(surf, (30, 30, 30), (body.centerx, body.y + 8), (body.centerx + 3, body.y + 8))
        pygame.draw.rect(surf, WOOD_D, (body.x + 4, body.y + 17, 8, 20))
        pygame.draw.circle(surf, GOLD, (body.centerx, body.y + 32), 2)
    elif ch == "S":                                         # staircase against a wall
        wall_top = r > 0 and M[r - 1][c] == "#"
        wall_right = c + bw < COLS and M[r][c + bw] == "#"
        pygame.draw.rect(surf, (210, 200, 184), rect)
        if wall_right and not wall_top:                     # back stairs climbing to the right
            steps = rect.w // 6
            for i in range(steps):
                pygame.draw.rect(surf, shade((206, 196, 178), -i * 6), (rect.x + i * 6, rect.y + 2, 5, rect.h - 4))
        else:
            steps = rect.h // 6
            for i in range(steps):
                k = i if wall_top else steps - 1 - i       # darker towards the wall = going away
                yy = rect.y + i * 6
                pygame.draw.rect(surf, shade((214, 204, 188), -(steps - k) * 5), (rect.x + 4, yy, rect.w - 8, 5))
            run = pygame.Rect(rect.centerx - min(24, rect.w // 3), rect.y, min(48, rect.w * 2 // 3), rect.h)
            pygame.draw.rect(surf, (150, 92, 80), run)                               # muted runner
            for i in range(steps):
                pygame.draw.line(surf, GOLD, (run.x, rect.y + i * 6 + 5), (run.right - 1, rect.y + i * 6 + 5))
            for bx in (rect.x, rect.right - 5):
                pygame.draw.rect(surf, WOOD_D, (bx, rect.y, 5, rect.h))
                pygame.draw.circle(surf, WOOD, (bx + 2, rect.bottom - 2 if wall_top else rect.y + 2), 4)
    elif ch == "u":                                         # stone fountain
        pygame.draw.ellipse(surf, (196, 190, 176), rect.inflate(-2, -2))
        pygame.draw.ellipse(surf, (170, 164, 150), rect.inflate(-2, -2), 2)
        pygame.draw.ellipse(surf, (130, 176, 196), rect.inflate(-10, -10))
        pygame.draw.circle(surf, (214, 208, 194), rect.center, 7)
        pygame.draw.circle(surf, (200, 230, 244), (rect.centerx, rect.centery - 8), 3)
        for a in range(6):
            ang = a * math.pi / 3
            pygame.draw.circle(surf, (220, 240, 250),
                               (int(rect.centerx + math.cos(ang) * 16), int(rect.centery + math.sin(ang) * 12)), 1)
    elif ch == "r":                                         # rose bush
        pygame.draw.circle(surf, (64, 98, 60), (x + 16, y + 18), 13)
        pygame.draw.circle(surf, (86, 124, 76), (x + 13, y + 14), 8)
        rnd = random.Random(c * 3 + r * 11)
        for _ in range(7):
            pygame.draw.circle(surf, rnd.choice([(214, 120, 128), (236, 200, 196), (190, 90, 100), (244, 230, 220)]),
                               (x + rnd.randint(6, 26), y + rnd.randint(8, 28)), 2)
    elif ch == "H":                                         # planter box / clipped hedge
        if room == "rosegarden":
            pygame.draw.rect(surf, (60, 92, 58), rect.inflate(-2, -2).move(0, 2), border_radius=8)
            pygame.draw.rect(surf, (86, 126, 76), rect.inflate(-2, -4), border_radius=8)
            rnd = random.Random(c * 7 + r)
            for _ in range(bw * 4):
                pygame.draw.circle(surf, (104, 146, 90), (rect.x + rnd.randint(6, rect.w - 6), rect.y + rnd.randint(6, 22)), 3)
        else:
            _shadow(surf, rect.inflate(-2, -2))
            pygame.draw.rect(surf, WOOD_D, rect.inflate(-2, -2).move(0, 2))
            pygame.draw.rect(surf, (156, 118, 82), rect.inflate(-2, -4))
            pygame.draw.rect(surf, (96, 72, 52), rect.inflate(-8, -10))
            rnd = random.Random(c * 5 + r * 9)
            for k in range(bw * 3):
                fx, fy = rect.x + 6 + k * (rect.w - 12) // max(1, bw * 3 - 1), rect.y + 12 + rnd.randint(-3, 3)
                pygame.draw.line(surf, (80, 120, 70), (fx, fy + 6), (fx, fy), 1)
                pygame.draw.circle(surf, rnd.choice([(230, 170, 210), (250, 246, 250), (190, 140, 210), (240, 210, 120)]), (fx, fy), 3)
    elif ch == "n":                                         # white wrought-iron bench
        b = rect.inflate(-2, -10)
        _shadow(surf, b)
        pygame.draw.rect(surf, (236, 236, 230), b, border_radius=3)
        pygame.draw.rect(surf, (190, 190, 186), b, 1, border_radius=3)
        for k in range(b.x + 4, b.right - 2, 4):
            pygame.draw.line(surf, (200, 200, 196), (k, b.y + 2), (k, b.bottom - 3))
        pygame.draw.rect(surf, (236, 236, 230), (b.x, b.y - 4, b.w, 4), border_radius=2)
    elif ch == "v":                                         # marble pedestal
        pygame.draw.rect(surf, (184, 178, 168), (x + 9, y + 26, 14, 4))
        pygame.draw.rect(surf, (226, 222, 214), (x + 11, y + 14, 10, 13))
        pygame.draw.line(surf, (200, 196, 188), (x + 13, y + 15), (x + 13, y + 25))
        pygame.draw.ellipse(surf, (184, 178, 168), (x + 5, y + 11, 22, 7))
        pygame.draw.ellipse(surf, (240, 238, 232), (x + 5, y + 10, 22, 6))
    elif ch == "p":                                         # potted palm
        pygame.draw.rect(surf, (226, 220, 206), (x + 10, y + 19, 12, 11), border_radius=2)
        pygame.draw.line(surf, GOLD_D, (x + 10, y + 22), (x + 21, y + 22), 1)
        for a in range(7):
            ang = math.pi + a * math.pi / 6
            ex, ey = x + 16 + math.cos(ang) * 13, y + 16 + math.sin(ang) * 11
            pygame.draw.line(surf, (70, 110, 70), (x + 16, y + 19), (ex, ey), 3)
            pygame.draw.line(surf, (110, 150, 100), (x + 16, y + 19), (ex, ey), 1)


def build_background():
    lv = level()
    bg = pygame.Surface((COLS * TILE, ROWS * TILE))
    M = logic.MAP
    for r in range(ROWS):
        for c in range(COLS):
            if M[r][c] != "#":
                draw_floor(bg, c, r)
    for c, r, w, h in RUNNERS[lv]:
        rect = pygame.Rect(c * TILE + 4, r * TILE + 4, w * TILE - 8, h * TILE - 8)
        pygame.draw.rect(bg, (150, 100, 86), rect)
        pygame.draw.rect(bg, CREAM, rect.inflate(-4, -4), 1)
    for c, r, w, h, base, border in RUGS[lv]:
        draw_rug(bg, pygame.Rect(c * TILE + 4, r * TILE + 4, w * TILE - 8, h * TILE - 8), base, border)
    for r in range(ROWS):
        for c in range(COLS):
            if M[r][c] == "#":
                draw_wall(bg, c, r)
    for r in range(ROWS):
        for c in range(COLS):
            ch = M[r][c]
            if ch not in "#.Dw":
                draw_furniture(bg, c, r, ch)
    glow = pygame.Surface(bg.get_size(), pygame.SRCALPHA)
    for gx, gy in CHANDELIERS[lv]:
        for rad, a in ((90, 12), (60, 14), (34, 16)):
            pygame.draw.circle(glow, (255, 226, 160, a), (gx * TILE, gy * TILE + 16), rad)
    bg.blit(glow, (0, 0))
    return bg


def draw_fire(surf, t, hud_h):
    for c, r in fireplaces():
        x, y = c * TILE + 16, r * TILE + hud_h + TILE - 3
        for k in range(3):
            h = 7 + math.sin(t * 13 + k * 2.1 + c) * 3
            col = [(255, 120, 30), (255, 180, 50), (255, 240, 150)][k]
            w = 6 - k * 2
            pygame.draw.polygon(surf, col, [(x - w - 1, y), (x + w + 1, y),
                                            (x + math.sin(t * 9 + k) * 2, y - h + k * 2)])
