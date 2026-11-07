"""Пиксель-арт, нарисованный прямо в коде.

Каждый спрайт — список строк, каждый символ — пиксель (цвет из палитры).
'.' — прозрачный. Обводка добавляется автоматически.
Свою картинку можно положить в папку assets/ (PNG с прозрачным фоном),
она подхватится вместо встроенной: cat_0.png, cat_1.png, fox_0.png, fox_1.png,
blackcat_0.png, blackcat_1.png, gran_0.png, gran_1.png.
"""
import os
import pygame

PALETTE = {
    # кот
    "O": (150, 100, 66),   # шерсть — приятный коричневый
    "o": (92, 58, 36),     # полоски
    "W": (250, 246, 238),  # белое (носочки, мордочка)
    "E": (110, 200, 90),   # глаза
    "P": (236, 140, 150),  # нос
    # лис
    "F": (236, 112, 36),
    "f": (190, 80, 24),
    "k": (40, 30, 30),
    "e": (30, 24, 20),
    # чёрная кошка
    "N": (54, 48, 62),
    "n": (32, 28, 38),
    "Y": (250, 214, 60),
    "p": (180, 110, 130),
    # бабушка
    "C": (178, 142, 214),  # пастельный сиреневый костюм и шляпка
    "c": (138, 104, 180),
    "h": (236, 236, 244),  # седые кудри
    "S": (246, 206, 176),  # кожа
    "M": (206, 104, 128),  # помада
    "w": (255, 255, 255),  # жемчуг
    "t": (224, 198, 180),  # чулки
    "K": (44, 36, 46),     # сумочка и туфли
    "G": (244, 150, 186),  # цветок на шляпке, румянец
    # прочее
    "R": (232, 52, 72),
    "r": (150, 30, 50),
    # предметы
    "B": (120, 180, 236),  # рыбка
    "b": (64, 116, 186),
    "T": (206, 128, 56),   # жареная курица
    "u": (160, 88, 34),
    "V": (242, 244, 250),  # ваза — белый фарфор
    "v": (52, 86, 170),    # синий узор
    "g": (70, 160, 80),    # стебель
}
OUTLINE = (28, 22, 30)

# Кот: коричневый, в полоску, белые носочки. Смотрит вправо.
CAT_0 = [
    "...........O...O",
    "..O.......OoOoO.",
    "..o.......OEOOE.",
    "..O.......OOOOOP",
    "...o.....OOWWWO.",
    "...OOOOOOOOOWWO.",
    "...OoOOoOOoOOW..",
    "...OoOOoOOoOOW..",
    "...OOoOOoOOoOO..",
    "...OO.OO..OO.OO.",
    "...WW.WW..WW.WW.",
    "...WW.WW..WW.WW.",
]
CAT_1 = CAT_0[:9] + [
    "....OO.OO.OO.OO.",
    "....WW.WW.WW.WW.",
    "....WW.WW.WW.WW.",
]

# Лис: рыжий, белая грудка и кончик хвоста, чёрные лапки.
FOX_0 = [
    "...........k..k.",
    "...........F..F.",
    "..........FFFFF.",
    "..........FeFFFF",
    ".W........FFWWWk",
    "WWF.......FWWW..",
    "WFFF.....FFWW...",
    ".FFFFFFFFFFWWF..",
    "..FFFFFFFFFFFFF.",
    "...ffFFFFFFFFff.",
    "...f...f..f...f.",
    "...k...k..k...k.",
]
FOX_1 = FOX_0[:10] + [
    "....f.f....f.f..",
    "....k.k....k.k..",
]

# Чёрная кошка — тот же силуэт кота, перекрашенный, и в полтора раза крупнее.
_BLACK = str.maketrans({"O": "N", "o": "n", "W": "N", "E": "Y", "P": "p"})
BLACKCAT_0 = [r.translate(_BLACK) for r in CAT_0]
BLACKCAT_1 = [r.translate(_BLACK) for r in CAT_1]

# Бабушка: элегантный пастельный костюм, шляпка в тон, жемчуг, сумочка.
GRAN_0 = [
    ".....ccc........",
    "....CCCCCC......",
    "...CCCCCCCCG....",
    "..cccccccccccc..",
    "...hhhhSSSS.....",
    "..hhhhSSSeS.....",
    "..hhhSSSSSSS....",
    "..hhhSSGSSS.....",
    "...hhSSSMS......",
    "....hSSSS.......",
    ".....SSS........",
    "...CwCwCwCC.....",
    "..CCCCCCCCCC....",
    "..CCCCCwCCCC....",
    "..CcCCCCCCcCC...",
    "..CcCCCwCCcSS...",
    "..CCCCCCCCCKKK..",
    "..CCCCCCCCKKKKK.",
    "..cccccccccKKK..",
    "...CCCCCCCC.....",
    "...CCCCCCCC.....",
    "....tt..tt......",
    "....tt..tt......",
    "...KKK.KKK......",
]
GRAN_1 = GRAN_0[:21] + [
    "....tt...tt.....",
    "...tt....tt.....",
    "..KKK....KKK....",
]

FISH = [
    "..bbbb...b",
    ".bBBBBb.bb",
    "bBeBBBBbBb",
    ".bBBBBb.bb",
    "..bbbb...b",
]

CHICKEN = [
    "..TTTT...",
    ".TTTTTu..",
    "TTTTTTTu.",
    "TTTTTTTu.",
    ".uTTTTu..",
    "..uuuW...",
    "......WW.",
    ".....W..W",
]

VASE = [
    ".R.G.",
    "RgRgG",
    "..g..",
    ".VVV.",
    "VvVvV",
    "VVVVV",
    ".vVv.",
]

HEART = [
    ".RR.RR.",
    "RRRRRRR",
    "RRRRRRR",
    ".RRRRR.",
    "..RRR..",
    "...R...",
]
HEART_EMPTY = [r.replace("R", "r") for r in HEART]

STAR = [
    "..Y..",
    ".YYY.",
    "YYYYY",
    ".YYY.",
    ".Y.Y.",
]


def _from_rows(rows, scale, outline=OUTLINE):
    w = max(len(r) for r in rows) + 2
    h = len(rows) + 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    grid = [[None] * w for _ in range(h)]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                grid[y + 1][x + 1] = PALETTE[ch]
    for y in range(h):
        for x in range(w):
            if grid[y][x]:
                surf.set_at((x, y), grid[y][x])
            elif outline and any(
                0 <= x + dx < w and 0 <= y + dy < h and grid[y + dy][x + dx]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                surf.set_at((x, y), outline)
    return pygame.transform.scale(surf, (w * scale, h * scale))


def _load(name, rows, scale, outline=OUTLINE):
    path = os.path.join(os.path.dirname(__file__), "assets", name + ".png")
    if os.path.exists(path):
        return pygame.image.load(path).convert_alpha()
    return _from_rows(rows, scale, outline)


def load_all():
    s = {}
    chars = (
        ("cat", (CAT_0, CAT_1), 2, OUTLINE),
        ("fox", (FOX_0, FOX_1), 2, OUTLINE),
        ("blackcat", (BLACKCAT_0, BLACKCAT_1), 3, (120, 96, 150)),
        ("gran", (GRAN_0, GRAN_1), 2, OUTLINE),
    )
    for key, rows, scale, outline in chars:
        frames = [_load(f"{key}_{i}", r, scale, outline) for i, r in enumerate(rows)]
        s[key] = {1: frames, -1: [pygame.transform.flip(f, True, False) for f in frames]}
    s["star"] = _from_rows(STAR, 2)
    s["fish"] = _from_rows(FISH, 2)
    s["chicken"] = _from_rows(CHICKEN, 2)
    s["vase"] = _from_rows(VASE, 2)
    s["heart"] = _from_rows(HEART, 2)
    s["heart_empty"] = _from_rows(HEART_EMPTY, 2)
    s["cat_icon"] = pygame.transform.scale(s["cat"][1][0], (28, 24))
    s["fox_icon"] = pygame.transform.scale(s["fox"][1][0], (28, 22))
    s["blackcat_icon"] = pygame.transform.scale(s["blackcat"][1][0], (20, 17))
    s["gran_icon"] = pygame.transform.scale(s["gran"][1][0], (14, 20))
    return s
