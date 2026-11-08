"""Pixel art drawn right in the code.

Each sprite is a list of strings; each character is a pixel (a palette color).
'.' is transparent. The outline is added automatically.
You can drop your own image into assets/ (PNG with transparency)
and it will replace the built-in one: cat_0.png, cat_1.png, fox_0.png, fox_1.png,
blackcat_0.png, blackcat_1.png, gran_0.png, gran_1.png,
janis_0.png, janis_1.png.
"""
import os
import pygame

PALETTE = {
    # cat
    "O": (150, 100, 66),   # fur, a nice brown
    "o": (92, 58, 36),     # stripes
    "W": (250, 246, 238),  # white (socks, muzzle)
    "E": (110, 200, 90),   # eyes
    "P": (236, 140, 150),  # nose
    # fox
    "F": (236, 112, 36),
    "f": (190, 80, 24),
    "k": (40, 30, 30),
    "e": (30, 24, 20),
    # black cat
    "N": (66, 60, 76),
    "n": (44, 40, 52),
    "Y": (250, 214, 60),
    "p": (180, 110, 130),
    # grandma
    "C": (178, 142, 214),  # pastel lilac suit and hat
    "c": (138, 104, 180),
    "h": (236, 236, 244),  # grey curls
    "S": (246, 206, 176),  # skin
    "M": (206, 104, 128),  # lipstick
    "w": (255, 255, 255),  # pearls
    "t": (224, 198, 180),  # stockings
    "K": (44, 36, 46),     # handbag and shoes
    "G": (244, 150, 186),  # hat flower, blush
    # Janis
    "J": (52, 60, 92),     # navy three-piece suit
    "j": (36, 42, 66),
    "q": (132, 34, 54),    # burgundy waistcoat and bow tie
    "d": (62, 62, 76),     # trousers
    "L": (196, 156, 60),   # brass lantern and buttons
    "x": (198, 198, 208),  # grey hair
    "X": (120, 120, 136),  # darker grey: brows, hair shading, sideburns
    "z": (176, 112, 104),  # lips
    "Z": (222, 170, 142),  # wrinkles
    # misc
    "R": (232, 52, 72),
    "r": (150, 30, 50),
    # items
    "B": (120, 180, 236),  # fish
    "b": (64, 116, 186),
    "T": (206, 128, 56),   # roast chicken
    "u": (160, 88, 34),
    "V": (242, 244, 250),  # vase, white porcelain
    "v": (52, 86, 170),    # blue pattern
    "g": (70, 160, 80),    # stem
}
OUTLINE = (28, 22, 30)

# Kitten: brown, striped, white socks. Faces right. A big head, a small body and short thin
# legs (shorter than the fox's). Frame 0 = standing, frames 1-4 = walk cycle.
_KITTEN_TOP = [
    ".........O....O",
    ".........OO..OO",
    ".o.......OOOOOO",
    ".O.......OEOOEO",
    ".O.......OOOOOP",
    "..O......OOWWO.",
    "..OoOOoOOoOWW..",
    "..OoOOoOOoOW...",
    "..OOOOOOOOOO...",
]
_KITTEN_TAIL_B = [                      # tail swung back a little
    ".........O....O",
    ".........OO..OO",
    "o........OOOOOO",
    ".O.......OEOOEO",
    ".O.......OOOOOP",
    "..O......OOWWO.",
]
_KITTEN_LEGS = [
    ["..O.O....O.O...", "..W.W....W.W..."],     # standing
    [".O..O...O..O...", ".W..W...W..W..."],     # stride
    ["...OO....OO....", "...WW....WW...."],     # passing
    ["..O..O...O..O..", "..W..W...W..W.."],     # stride, other legs
    ["...OO....OO....", "...WW....WW...."],     # passing
]
CAT_FRAMES = []
for _i, _legs in enumerate(_KITTEN_LEGS):
    _top = (_KITTEN_TAIL_B + _KITTEN_TOP[6:]) if _i in (2, 3) else _KITTEN_TOP
    CAT_FRAMES.append(_top + _legs)
CAT_0, CAT_1 = CAT_FRAMES[0], CAT_FRAMES[1]

# Fox: orange, white chest and tail tip, black paws.
_FOX_TOP = [
    "..........k...k.",
    "..........FF.FF.",
    "..........FF.FF.",
    "..........FFFFF.",
    "..........FeFFFF",
    ".W........FFWWWk",
    "WWF.......FFWW..",
    "WFFF......FWWW..",
    ".FFFFFFFFFFWWW..",
    "..FFFFFFFFFFFF..",
    "...ffFFFFFFFff..",
]
_FOX_TAIL_B = [                         # tail swung up a little
    "..........k...k.",
    "..........FF.FF.",
    "..........FF.FF.",
    "..........FFFFF.",
    "W.........FeFFFF",
    "WW........FFWWWk",
    "WFF.......FFWW..",
    ".FFF......FWWW..",
]
_FOX_LEGS = [
    ["...f...f..f..f..", "...f...f..f..f..", "...k...k..k..k.."],     # standing
    ["..f...f...f...f.", "..f...f...f...f.", "..k...k...k...k."],     # stride
    ["....ff.....ff...", "....ff.....ff...", "....kk.....kk..."],     # passing
    ["...f..f....f..f.", "...f..f....f..f.", "...k..k....k..k."],     # stride, other legs
    ["....ff.....ff...", "....ff.....ff...", "....kk.....kk..."],     # passing
]
FOX_FRAMES = []
for _i, _legs in enumerate(_FOX_LEGS):
    _top = (_FOX_TAIL_B + _FOX_TOP[8:]) if _i in (2, 3) else _FOX_TOP
    FOX_FRAMES.append(_top + _legs)
FOX_0, FOX_1 = FOX_FRAMES[0], FOX_FRAMES[1]

# Sitting poses (after standing still for a moment): tail wrapped round the paws.
FOX_SIT = [
    "..........k...k.",
    "..........FF.FF.",
    "..........FF.FF.",
    "..........FFFFF.",
    "..........FeFFFF",
    "..........FFWWWk",
    ".........FFWWW..",
    "........FFFWWW..",
    ".......FFFFWWW..",
    ".......FFFFFFF..",
    "......FFFFFFFF..",
    "...WWFFFFFFkFk..",
]
CAT_SIT = [
    ".........O....O",
    ".........OO..OO",
    ".........OOOOOO",
    ".........OEOOEO",
    ".........OOOOOP",
    ".........OOWWO.",
    "........OOOWW..",
    ".......OOoOWW..",
    "......OOOoOOW..",
    "......OOOOOOW..",
    "....ooOOOOOWW..",
]

# Black cat: the same cute style as the kitten, but grown-up and the size of the fox.
# Big round head, upright ears, yellow eyes, a pink nose.
_BLACK_TOP = [
    ".........N....N.",
    ".........NN..NN.",
    ".n.......NNNNNN.",
    ".N.......NNNNNN.",
    ".N.......NYNNYN.",
    "..N......NNNNNp.",
    "..NNNNNNNNNNNN..",
    "..NNNNNNNNNNNN..",
    "..NNNNNNNNNNNN..",
    "...nnnnnnnnnnn..",
]
_BLACK_TAIL_B = [
    ".........N....N.",
    ".........NN..NN.",
    "n........NNNNNN.",
    ".N.......NNNNNN.",
    ".N.......NYNNYN.",
    "..N......NNNNNp.",
]
_BLACK_LEGS = [
    ["...N..N...N..N..", "...N..N...N..N..", "...N..N...N..N.."],
    ["..N...N..N...N..", "..N....N.N....N.", ".N.....N.N.....N"],
    ["....NN....NN....", "....NN....NN....", "....NN....NN...."],
    ["...N...N..N...N.", "...N....N.N....N", "...N....NN.....N"],
    ["....NN....NN....", "....NN....NN....", "....NN....NN...."],
]
BLACKCAT_FRAMES = []
for _i, _legs in enumerate(_BLACK_LEGS):
    _top = (_BLACK_TAIL_B + _BLACK_TOP[6:]) if _i in (2, 3) else _BLACK_TOP
    BLACKCAT_FRAMES.append(_top + _legs)
BLACKCAT_0, BLACKCAT_1 = BLACKCAT_FRAMES[0], BLACKCAT_FRAMES[1]
BLACKCAT_SIT = [
    ".........N....N.",
    ".........NN..NN.",
    ".........NNNNNN.",
    ".........NYNNYN.",
    ".........NNNNNp.",
    ".........NNNNN..",
    "........NNNNNN..",
    ".......NNNNNNN..",
    "......NNNNNNNN..",
    "......NNNNNNNN..",
    "....NNNNNNNNNN..",
    "...nnnnnnnnnnn..",
]

# Being carried in someone's arms: head upright as usual, front paws poking out under the arm,
# the rest of the body, the back legs and the tail hanging straight down.
CAT_HELD = [
    ".O....O.",
    ".OO..OO.",
    ".OOOOOO.",
    ".OEOOEO.",
    ".OOOOOOP",
    "..OWWO..",
    "..OOWO..",
    ".WOoOOW.",
    "..OoOO..",
    "..OOoO..",
    "..OOOO..",
    "..OoOO..",
    "..O..O..",
    "..W..W..",
    "...oO...",
    "....O...",
    "....o...",
]
FOX_HELD = [
    ".k...k..",
    ".FF.FF..",
    ".FF.FF..",
    ".FFFFF..",
    ".FeFFFF.",
    ".FFWWWk.",
    "..FWWW..",
    ".kFWWFk.",
    "..FWWF..",
    "..FFFF..",
    "..FFFF..",
    "..ffff..",
    "..f..f..",
    "..k..k..",
    "...FF...",
    "...FF...",
    "...FF...",
    "...WW...",
]

# Asleep on a pet bed: curled up, eyes closed.
CAT_SLEEP = [
    "..........O..O.",
    "..........OOOO.",
    "...OOoOOoOOooO.",
    "..OOoOOoOOOOOOP",
    "..OOOOOOOOOWWW.",
    "..ooooooWW.....",
]
FOX_SLEEP = [
    "..........k...k.",
    "..........FF.FF.",
    "...FFFFFF.FFFFF.",
    "..FFFFFFFFFkFFFF",
    ".FFFFFFFFFFFWWk.",
    ".FFFFFFFFFFFWW..",
    "...FFFFFFFFFFWW.",
]

# Extra poses for the idle animation. Blinking frames are made by closing the eyes.
POSES = {
    "cat": {"sit": CAT_SIT, "tail": _KITTEN_TAIL_B + _KITTEN_TOP[6:] + _KITTEN_LEGS[0]},
    "blackcat": {"sit": BLACKCAT_SIT, "tail": _BLACK_TAIL_B + _BLACK_TOP[6:] + _BLACK_LEGS[0]},
    "fox": {"sit": FOX_SIT, "tail": _FOX_TAIL_B + _FOX_TOP[8:] + _FOX_LEGS[0]},
}
EYES = {"cat": ("E", "O"), "blackcat": ("Y", "N"), "fox": ("e", "F")}   # eye colour -> fur colour

# Grandma: elegant pastel suit, matching hat, pearls, handbag.
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

# Janis: a stern old lord to match Yolanta. Tall and broad-shouldered, a full head of
# grey hair with a swept fringe, heavy brows, a few wrinkles, double-breasted suit, lantern.
JANIS_0 = [
    "....xxxxxxx.....",
    "...xxXxxxxxx....",
    "...xxxSSSSS.....",
    "...xxSSSXXS.....",
    "...xxSSZSeS.....",
    "...xxSSSSSSS....",
    "...xxSSSSSS.....",
    "...xxSSSzzS.....",
    "....xSSSSS......",
    "....SSSZS.......",
    ".....SSSS.......",
    "....WWqqWW......",
    "..JJJWqqWJJJ....",
    ".JJJJJqqJJJJJ...",
    ".JjJLJJWJLJjJ...",
    ".JjJJJJJJJJjJS..",
    ".JjJLJJJJLJjJ.L.",
    ".JjJJJJJJJJjJLYL",
    ".JJJJJJJJJJJJLYL",
    "..JJJJJJJJJJ..L.",
    "..JJJJ..JJJJ....",
    "...dd....dd.....",
    "...dd....dd.....",
    "...dd....dd.....",
    "...dd....dd.....",
    "..KKK...KKK.....",
]
JANIS_1 = JANIS_0[:JANIS_0.index("...dd....dd.....")] + [
    "...dd.....dd....",
    "..dd......dd....",
    "..dd......dd....",
    "..dd......dd....",
    ".KKK......KKK...",
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
        ("cat", CAT_FRAMES, 2, OUTLINE),
        ("fox", FOX_FRAMES, 2, OUTLINE),
        ("blackcat", BLACKCAT_FRAMES, 2, OUTLINE),
        ("gran", (GRAN_0, GRAN_1), 2, OUTLINE),
        ("janis", (JANIS_0, JANIS_1), 2, OUTLINE),
    )
    for key, rows, scale, outline in chars:
        frames = [_load(f"{key}_{i}", r, scale, outline) for i, r in enumerate(rows)]
        s[key] = {1: frames, -1: [pygame.transform.flip(f, True, False) for f in frames]}
    stands = {"cat": CAT_FRAMES[0], "blackcat": BLACKCAT_FRAMES[0], "fox": FOX_FRAMES[0]}
    for key, poses in POSES.items():
        eye, fur = EYES[key]
        rows = dict(poses, stand=stands[key])
        for name in ("stand", "sit"):
            rows[name + "_blink"] = [r.replace(eye, fur) for r in rows[name]]
        surfs = {name: _load(f"{key}_{name}", rr, 2) for name, rr in rows.items()}
        s[key + "_pose"] = {1: surfs, -1: {n: pygame.transform.flip(f, True, False) for n, f in surfs.items()}}
    for key, rows in (("cat", CAT_HELD), ("fox", FOX_HELD)):
        surf = _load(f"{key}_held", rows, 2)
        s[key + "_held"] = {1: surf, -1: pygame.transform.flip(surf, True, False)}
    for key, rows in (("cat", CAT_SLEEP), ("fox", FOX_SLEEP)):
        surf = _load(f"{key}_sleep", rows, 2)
        s[key + "_sleep"] = {1: surf, -1: pygame.transform.flip(surf, True, False)}
    s["star"] = _from_rows(STAR, 2)
    s["fish"] = _from_rows(FISH, 2)
    s["chicken"] = _from_rows(CHICKEN, 2)
    s["vase"] = _from_rows(VASE, 2)
    s["heart"] = _from_rows(HEART, 2)
    s["heart_empty"] = _from_rows(HEART_EMPTY, 2)
    s["cat_icon"] = pygame.transform.scale(s["cat"][1][0], (28, 22))
    s["fox_icon"] = pygame.transform.scale(s["fox"][1][0], (28, 22))
    s["blackcat_icon"] = pygame.transform.scale(s["blackcat"][1][0], (22, 17))
    s["gran_icon"] = pygame.transform.scale(s["gran"][1][0], (14, 20))
    return s
