"""Locations of the manor. Each round of a match is played on a random one.

A level is built from rooms, walls, doors and furniture, so it's easy to edit.
  # wall   D door   . floor
  w wardrobe (the cat hides in it)   v vase on a pedestal
  k counter / washstand / cupboard   o kitchen range   t table   T dining table   f sideboard / nightstand
  L shelves (books, silver, wine)    d desk   s sofa   a armchair   P grand piano   I column
  R round hall table with flowers    b bed    h bathtub / wash tub   e dressing table
  y rocking horse   g barrel   p potted palm   x marble bust / statue   c grandfather clock   S staircase
  r rose bush   u fountain   H planter box / low hedge   n garden bench
"""
COLS, ROWS = 40, 21
SOLID = set("#wvkotTfLdsaPIRbheygpxcSBruHn")


def build(spec):
    g = [["."] * COLS for _ in range(ROWS)]

    def put(ch, c, r, w=1, h=1):
        for y in range(r, r + h):
            for x in range(c, c + w):
                g[y][x] = ch

    put("#", 0, 0, COLS, 1)
    put("#", 0, ROWS - 1, COLS, 1)
    put("#", 0, 0, 1, ROWS)
    put("#", COLS - 1, 0, 1, ROWS)
    for wall in spec["walls"]:
        put("#", *wall)
    for c, r in spec["doors"]:
        g[r][c] = "D"
    for item in spec["furniture"]:
        put(*item)
    return ["".join(row) for row in g]


GROUND = dict(
    name="ground", title="The Ground Floor",
    rooms=[("drawing", 1, 1, 12, 9), ("library", 1, 11, 12, 19), ("hall", 14, 1, 25, 19),
           ("dining", 27, 1, 38, 9), ("study", 27, 11, 38, 19)],
    walls=[(13, 1, 1, 19), (26, 1, 1, 19), (1, 10, 12, 1), (27, 10, 12, 1)],
    doors=[(13, 5), (13, 15), (26, 5), (26, 15), (6, 10), (32, 10)],
    front_door=[(19, 20), (20, 20)],
    furniture=[
        # drawing room
        ("w", 1, 1), ("s", 5, 3, 3, 1), ("a", 3, 5), ("a", 9, 5), ("t", 5, 6, 3, 1),
        ("P", 10, 7, 2, 2), ("p", 1, 9), ("v", 12, 9),
        # library
        ("L", 1, 11, 4, 1), ("L", 8, 11, 5, 1), ("L", 3, 14, 2, 2), ("L", 8, 14, 2, 2),
        ("v", 1, 16), ("t", 5, 17, 3, 1), ("a", 1, 19), ("w", 12, 19),
        # grand hall
        ("S", 17, 1, 6, 3), ("c", 14, 2), ("x", 25, 2), ("I", 15, 6), ("I", 24, 6), ("I", 15, 13), ("I", 24, 13),
        ("R", 19, 9, 2, 2), ("v", 16, 16), ("v", 23, 16), ("p", 14, 19), ("p", 25, 19),
        # dining room
        ("f", 28, 1), ("f", 37, 1), ("T", 29, 4, 8, 2), ("v", 27, 9), ("w", 38, 9),
        # study
        ("L", 35, 11, 4, 1), ("a", 32, 14), ("d", 31, 15, 3, 1), ("s", 28, 18, 3, 1),
        ("v", 38, 15), ("x", 27, 11), ("w", 38, 19),
    ],
    cat_spawn=(6, 16), fox_spawn=(33, 7), switches=[(15, 1), (29, 11)], food_room="dining",
    residents={"janis": ["study", "dining"], "yolanta": ["drawing", "library"]}, carrier=(34, 17),
)

UPPER = dict(
    name="upper", title="The Upper Floor",
    rooms=[("master", 1, 1, 13, 7), ("boudoir", 15, 1, 23, 7), ("guest", 25, 1, 38, 7),
           ("gallery", 1, 9, 38, 11), ("nursery", 1, 13, 10, 19), ("bath", 12, 13, 17, 19),
           ("landing", 19, 13, 24, 19), ("guest2", 26, 13, 38, 19)],
    walls=[(1, 8, 38, 1), (1, 12, 38, 1), (14, 1, 1, 7), (24, 1, 1, 7),
           (11, 13, 1, 7), (18, 13, 1, 7), (25, 13, 1, 7)],
    doors=[(6, 8), (19, 8), (31, 8), (14, 4), (24, 4),
           (5, 12), (15, 12), (21, 12), (22, 12), (32, 12), (11, 16), (18, 16), (25, 16)],
    front_door=[],
    furniture=[
        # master bedroom
        ("w", 1, 1), ("f", 4, 1), ("b", 5, 1, 3, 3), ("f", 8, 1), ("e", 12, 1), ("a", 11, 4), ("v", 13, 7),
        # boudoir
        ("e", 17, 1, 2, 1), ("w", 23, 1), ("s", 20, 4, 3, 1), ("a", 16, 5), ("v", 15, 7),
        # guest bedroom
        ("f", 29, 1), ("b", 30, 1, 2, 3), ("f", 32, 1), ("w", 38, 1), ("a", 36, 5), ("d", 26, 6, 2, 1),
        # portrait gallery
        ("p", 1, 9), ("x", 10, 9), ("c", 17, 9), ("x", 28, 9), ("p", 38, 9), ("v", 8, 11), ("v", 30, 11),
        # nursery
        ("y", 2, 14), ("f", 9, 13), ("t", 4, 17, 2, 1), ("b", 8, 17, 2, 2), ("w", 1, 19),
        # bathroom
        ("k", 12, 13), ("h", 14, 17, 3, 2), ("p", 17, 19),
        # landing with the staircase going down
        ("S", 20, 16, 4, 4),
        # second guest bedroom
        ("w", 38, 13), ("a", 28, 15), ("f", 34, 17), ("b", 35, 17, 2, 3), ("f", 37, 19), ("v", 26, 19),
    ],
    cat_spawn=(5, 15), fox_spawn=(31, 5), switches=[(12, 9), (34, 9)], food_room="master",
    residents={"janis": ["guest", "guest2"], "yolanta": ["master", "boudoir", "nursery"]}, carrier=(34, 5),
)

SERVICE = dict(
    name="service", title="The Service Floor",
    rooms=[("kitchen", 1, 1, 14, 9), ("scullery", 16, 1, 22, 5), ("larder", 16, 7, 22, 9),
           ("butler", 24, 1, 30, 9), ("cellar", 32, 1, 38, 9), ("passage", 1, 11, 38, 12),
           ("servants", 1, 14, 14, 19), ("laundry", 16, 14, 25, 19), ("housekeeper", 27, 14, 38, 19)],
    walls=[(1, 10, 38, 1), (1, 13, 38, 1), (15, 1, 1, 9), (23, 1, 1, 9), (31, 1, 1, 9),
           (16, 6, 7, 1), (15, 14, 1, 6), (26, 14, 1, 6)],
    doors=[(5, 10), (11, 10), (15, 3), (15, 8), (19, 6), (23, 3), (27, 10), (31, 6), (35, 10),
           (7, 13), (20, 13), (32, 13), (15, 17), (26, 16)],
    front_door=[],
    furniture=[
        # kitchen
        ("k", 1, 1, 3, 1), ("o", 6, 1, 3, 1), ("k", 11, 1, 2, 1), ("w", 14, 1),
        ("t", 5, 4, 5, 2), ("f", 1, 6), ("g", 1, 9), ("g", 13, 9),
        # scullery
        ("k", 18, 1, 3, 1), ("h", 16, 5),
        # larder
        ("L", 21, 7, 2, 1), ("g", 22, 9),
        # butler's pantry
        ("L", 24, 1, 2, 1), ("w", 30, 1), ("d", 27, 4, 2, 1), ("v", 30, 9),
        # wine cellar
        ("L", 32, 1, 3, 1), ("L", 36, 1, 3, 1), ("g", 33, 4), ("g", 34, 4), ("g", 36, 7), ("g", 37, 7),
        # service passage with the back stairs
        ("S", 37, 11, 2, 2),
        # servants' hall
        ("f", 1, 14), ("t", 4, 16, 6, 2), ("v", 1, 19), ("w", 14, 19),
        # laundry
        ("h", 17, 14, 2, 1), ("k", 24, 14), ("t", 19, 17, 3, 1), ("w", 16, 19),
        # housekeeper's room
        ("L", 37, 14, 2, 1), ("d", 33, 16, 2, 1), ("a", 36, 18), ("w", 27, 19), ("v", 38, 19),
    ],
    cat_spawn=(2, 17), fox_spawn=(36, 4), switches=[(28, 1), (12, 11)], food_room="kitchen",
    residents={"janis": ["butler", "cellar", "housekeeper"], "yolanta": ["kitchen", "servants", "laundry"]},
    carrier=(29, 6),
)

GARDEN = dict(
    name="garden", title="The Winter Garden",
    rooms=[("palmhouse", 1, 1, 12, 9), ("fountain", 14, 1, 25, 9), ("orchid", 27, 1, 38, 9),
           ("rosegarden", 1, 11, 17, 19), ("tearoom", 19, 11, 28, 19), ("potting", 30, 11, 38, 19)],
    walls=[(1, 10, 38, 1), (13, 1, 1, 9), (26, 1, 1, 9), (18, 11, 1, 9), (29, 11, 1, 9)],
    doors=[(13, 4), (26, 5), (6, 10), (20, 10), (33, 10), (18, 15), (29, 14)],
    front_door=[],
    furniture=[
        # palm house
        ("w", 1, 1), ("p", 5, 1), ("p", 9, 2), ("p", 2, 4), ("H", 5, 4, 3, 1), ("p", 11, 6),
        ("p", 3, 7), ("n", 8, 8, 2, 1), ("v", 1, 9),
        # fountain court
        ("v", 14, 1), ("r", 16, 2), ("r", 23, 2), ("u", 19, 4, 2, 2), ("v", 25, 1),
        ("n", 15, 6), ("n", 24, 6), ("r", 16, 8), ("r", 23, 8),
        # orchid room
        ("H", 29, 3, 8, 1), ("H", 29, 6, 8, 1), ("w", 38, 1), ("v", 27, 9), ("p", 38, 9),
        # rose garden
        ("r", 1, 11), ("r", 4, 11), ("r", 9, 11), ("r", 13, 11), ("v", 17, 11),
        ("H", 3, 13, 4, 1), ("H", 10, 13, 4, 1), ("x", 8, 15), ("H", 3, 17, 4, 1), ("H", 10, 17, 4, 1),
        ("r", 1, 15), ("r", 15, 15), ("n", 1, 19), ("r", 8, 19), ("p", 16, 19),
        # tea room
        ("a", 20, 13), ("t", 21, 13, 2, 1), ("a", 23, 13), ("t", 25, 13, 2, 1), ("a", 27, 13),
        ("a", 20, 17), ("t", 21, 17, 2, 1), ("a", 23, 17), ("t", 25, 17, 2, 1), ("a", 27, 17),
        ("p", 19, 19), ("v", 28, 19),
        # potting shed
        ("k", 35, 11, 2, 1), ("w", 38, 11), ("t", 34, 15, 3, 1), ("g", 30, 17), ("g", 31, 19), ("w", 38, 19),
    ],
    cat_spawn=(5, 15), fox_spawn=(32, 5), switches=[(16, 1), (32, 11)], food_room="tearoom",
    residents={"janis": ["potting", "orchid"], "yolanta": ["rosegarden", "palmhouse", "tearoom"]},
    carrier=(33, 17),
)

LEVELS = {spec["name"]: spec for spec in (GROUND, UPPER, SERVICE, GARDEN)}
for _spec in LEVELS.values():
    _spec["furniture"] = [it if len(it) == 5 else (*it, 1, 1) for it in _spec["furniture"]]
    _spec["map"] = build(_spec)
