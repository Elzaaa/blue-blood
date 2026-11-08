"""Blue Blood — the cat runs, the fox chases. A two-player game on one keyboard.

Run on desktop:     python main.py
Build for browser:  pygbag blueblood   (from the parent folder; see README)
"""
import asyncio
import json
import os
import sys
import math
import random

import pygame

import sprites
import logic
from logic import (COLS, ROWS, TILE, BLACKCAT_COOLDOWN, DASH_COOLDOWN,
                   FISH_WIN, FOX_HEARTS, GRAN_COOLDOWN, GRAN_HOLD, SCRATCH_TIME,
                   SNIFF_TIME, WARD_MAX, JANIS_HOLD, JANIS_KISS, Game, cell_center)

HUD_H = 48
W, H = COLS * TILE, ROWS * TILE + HUD_H
WINS_NEEDED = 3

# --- controls: each player gets their own side of the keyboard ----------
# Physical keys (scancodes) are used, so it works with any keyboard layout.
SIDES = [
    dict(up=pygame.KSCAN_W, down=pygame.KSCAN_S, left=pygame.KSCAN_A, right=pygame.KSCAN_D,
         act=(pygame.KSCAN_E, pygame.KSCAN_SPACE), summon=(pygame.KSCAN_Q,),
         names=("WASD", "E", "Q"), move=("W", "A", "S", "D")),
    dict(up=pygame.KSCAN_UP, down=pygame.KSCAN_DOWN, left=pygame.KSCAN_LEFT, right=pygame.KSCAN_RIGHT,
         act=(pygame.KSCAN_PERIOD, pygame.KSCAN_RETURN, pygame.KSCAN_KP_0, pygame.KSCAN_L),
         summon=(pygame.KSCAN_SLASH, pygame.KSCAN_RSHIFT, pygame.KSCAN_KP_1, pygame.KSCAN_K),
         names=("Arrows", ".", "/"), move=("UP", "LEFT", "DOWN", "RIGHT")),
]
PLAYER = ["Player 1", "Player 2"]
# True: the cat always plays on WASD + E + Q and the fox on the arrows, players swap seats.
# False: each player keeps their side of the keyboard and the keys swap with the roles.
CONTROLS = {"follow_role": True}
TIMERS = [90, 180, None]               # round length options; None = no timer
SETTINGS = {"timer": 90}


def timer_label(t):
    return "off" if t is None else f"{t // 60}:{t % 60:02d}"

CAT_COL = (222, 172, 128)
FOX_COL = (255, 128, 48)
PINK = (240, 140, 180)

# --- the manor is drawn in manor.py ---------------------------------------
import manor  # noqa: E402
import net  # noqa: E402
from manor import DOOR_C, DOOR_D, GOLD, build_background, draw_fire  # noqa: E402


# --- the original "House" look (toggle with T in the menu) -----------------
STYLE = {"name": "manor"}       # "manor" or "classic" (simple house)
CLASSIC_DOOR = ((150, 86, 40), (110, 60, 28), (240, 210, 90))
MANOR_DOOR = (DOOR_C, DOOR_D, GOLD)


def build_background_classic():
    MAP = logic.MAP
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
            if ch in "fktoTLBdaPruxcSIRbheygHn":
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
    pygame.draw.rect(surf, (72, 50, 34), body, border_radius=2)
    pygame.draw.rect(surf, (138, 100, 68), body.inflate(-4, -4), border_radius=2)
    pygame.draw.rect(surf, (158, 120, 84), (body.x + 1, body.y, body.w - 2, 6))
    pygame.draw.line(surf, GOLD, (body.x + 1, body.y + 6), (body.right - 2, body.y + 6))
    for px in (body.x + 4, body.centerx + 2):
        pygame.draw.rect(surf, (106, 76, 50), (px, body.y + 10, 10, body.h - 15), 1)
    pygame.draw.line(surf, (72, 50, 34), (body.centerx, body.y + 8), (body.centerx, body.bottom - 3), 2)
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


# --- effects ----------------------------------------------------------------
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


# --- input ------------------------------------------------------------------
def read_side(held, keys, side):
    k = SIDES[side]
    return {
        "dx": (k["right"] in held) - (k["left"] in held),
        "dy": (k["down"] in held) - (k["up"] in held),
        "act": any(x in keys for x in k["act"]),
        "summon": any(x in keys for x in k["summon"]),
    }


class Match:
    """Match score. Roles swap every round."""
    def __init__(self):
        self.wins = [0, 0]
        self.cat_player = 0
        self.round = 1
        self.done = False
        self.last = None
        self.level = random.choice(list(logic.LEVELS))

    def player_of(self, role):
        return self.cat_player if role == "cat" else 1 - self.cat_player

    def side_of(self, role):
        """Which side of the keyboard plays this role."""
        if CONTROLS["follow_role"]:
            return 0 if role == "cat" else 1
        return self.player_of(role)

    def finish_round(self, winner_role):
        self.last = self.player_of(winner_role)
        self.wins[self.last] += 1
        self.done = self.wins[self.last] >= WINS_NEEDED

    def next_round(self):
        self.cat_player = 1 - self.cat_player
        self.round += 1
        # a new random location, never the same one twice in a row
        self.level = random.choice([n for n in logic.LEVELS if n != self.level])

    def inputs(self, held, keys):
        return {"cat": read_side(held, keys, self.side_of("cat")),
                "fox": read_side(held, keys, self.side_of("fox"))}


# --- online play --------------------------------------------------------------
ONLINE_MOVE = {"up": (pygame.KSCAN_W, pygame.KSCAN_UP), "down": (pygame.KSCAN_S, pygame.KSCAN_DOWN),
               "left": (pygame.KSCAN_A, pygame.KSCAN_LEFT), "right": (pygame.KSCAN_D, pygame.KSCAN_RIGHT)}
ONLINE_ACT = (pygame.KSCAN_E, pygame.KSCAN_SPACE, pygame.KSCAN_PERIOD)
ONLINE_PERK = (pygame.KSCAN_Q, pygame.KSCAN_SLASH, pygame.KSCAN_LSHIFT, pygame.KSCAN_RSHIFT)
SERVER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.txt")


def load_server():
    try:
        with open(SERVER_FILE, encoding="utf-8") as f:
            return f.read().strip() or "localhost"
    except OSError:
        return "localhost"


def save_server(addr):
    try:
        with open(SERVER_FILE, "w", encoding="utf-8") as f:
            f.write(addr)
    except OSError:
        pass


def server_url(addr):
    """"1.2.3.4" -> ws://1.2.3.4:8765,  "my-game.onrender.com" -> wss://my-game.onrender.com"""
    addr = addr.strip()
    if addr.startswith(("ws://", "wss://")):
        return addr
    host = addr.split(":")[0]
    local = host == "localhost" or host.replace(".", "").isdigit() or host.endswith(".local")
    if ":" in addr or not local and "." not in host:
        return "ws://" + addr
    return f"ws://{addr}:{net.PORT}" if local else "wss://" + addr


class NetClient:
    """Talks to the server in the background while the game keeps drawing."""

    def __init__(self, addr):
        self.url = server_url(addr)
        self.status = "connecting"      # connecting | connected | left | error | closed
        self.error = None
        self.code = None
        self.meta = None
        self.snap = None
        self.events = []
        self.out = asyncio.Queue()
        self.task = asyncio.ensure_future(self.run())

    async def run(self):
        try:
            import websockets
        except ImportError:
            self.status, self.error = "error", "Install the network library first:  pip install websockets"
            return
        try:
            async with websockets.connect(self.url, open_timeout=8) as ws:
                self.status = "connected"
                sender = asyncio.ensure_future(self._send(ws))
                try:
                    async for raw in ws:
                        m = json.loads(raw)
                        if m["type"] == "room":
                            self.code = m["code"]
                        elif m["type"] == "state":
                            self.meta, self.snap = m["meta"], m["game"]
                            self.events.extend(m["game"]["ev"])
                        elif m["type"] == "error":
                            self.status, self.error = "error", m["text"]
                        elif m["type"] == "left":
                            self.status = "left"
                finally:
                    sender.cancel()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if self.status == "connecting":
                self.status, self.error = "error", f"Can't reach the server at {self.url}"
            elif self.status == "connected":
                self.status, self.error = "error", f"Lost connection ({e.__class__.__name__})"
            return
        if self.status == "connected":
            self.status = "closed"

    async def _send(self, ws):
        while True:
            await ws.send(json.dumps(await self.out.get()))

    def send(self, msg):
        self.out.put_nowait(msg)

    def take_events(self):
        ev, self.events = self.events, []
        return ev

    def close(self):
        self.task.cancel()


class NetMatch:
    """The match as the server describes it (same fields the renderer uses for a local match)."""

    def __init__(self, meta):
        self.wins, self.round, self.cat_player = meta["wins"], meta["round"], meta["cat_player"]
        self.last, self.done, self.you = meta["last"], meta["state"] == "done", meta["you"]

    def player_of(self, role):
        return self.cat_player if role == "cat" else 1 - self.cat_player

    def side_of(self, role):
        return 0                        # online everyone plays on their own keyboard


def online_input(held, keys):
    def on(names):
        return any(k in held for k in names)
    return {"dx": on(ONLINE_MOVE["right"]) - on(ONLINE_MOVE["left"]),
            "dy": on(ONLINE_MOVE["down"]) - on(ONLINE_MOVE["up"]),
            "act": any(k in keys for k in ONLINE_ACT), "summon": any(k in keys for k in ONLINE_PERK)}


# --- rendering --------------------------------------------------------------
class Renderer:
    def __init__(self, window):
        # The game is drawn on a 1280x720 canvas and scaled up to the real window without blur.
        # All text is collected and drawn at the window's full resolution on top, so it stays sharp.
        self.window = window
        self.screen = pygame.Surface((W, H))
        self.texts = []
        self._font_sizes = {}
        self._hi_fonts = {}
        self.bgs = {}     # (style, level) -> background, built on demand
        self.spr = sprites.load_all()
        self.spr["yolanta"] = self.spr["gran"]     # Yolanta as a house resident (vase noise)
        self.f_tiny = self.font(19)
        self.f_small = self.font(22)
        self.f_mid = self.font(30)
        self.f_big = self.font(56)
        self.f_huge = self.font(120)
        self.f_title = self.font(92)
        self.fx = Particles()
        self.popups = []
        self.trail = []
        self.shake = 0.0
        self.t = 0.0
        self.heart_t = 0.0
        self.idle = {}        # how long each character has been standing still
        self.viewer = None    # online: "cat" or "fox" (whose eyes we see the dark through)
        self.fish_icon = pygame.transform.scale(self.spr["fish"], (18, 10))
        self.fish_icon_dim = self.fish_icon.copy()
        self.fish_icon_dim.set_alpha(60)

    @property
    def bg(self):
        key = (STYLE["name"], logic.LEVEL["name"])
        if key not in self.bgs:
            self.bgs[key] = build_background() if key[0] == "manor" else build_background_classic()
        return self.bgs[key]

    def font(self, size):
        f = pygame.font.Font(None, size)
        self._font_sizes[id(f)] = size
        return f

    def text(self, s, font, color, center=None, topleft=None, shadow=True):
        """Queue text; it's drawn sharp at full resolution in present()."""
        w, h = font.size(s)
        rect = pygame.Rect(0, 0, w, h)
        if center:
            rect.center = center
        if topleft:
            rect.topleft = topleft
        self.texts.append((s, self._font_sizes.get(id(font), 24), color, rect, bool(topleft), shadow))
        return rect

    def present(self):
        """Scale the canvas to the window (no blur) and draw the queued text on top, sharp."""
        win = self.window
        ww, wh = win.get_size()
        scale = min(ww / W, wh / H)
        sw, sh = max(1, int(W * scale)), max(1, int(H * scale))
        ox, oy = (ww - sw) // 2, (wh - sh) // 2
        win.fill((0, 0, 0))
        if (sw, sh) == (W, H):
            win.blit(self.screen, (ox, oy))
        else:
            win.blit(pygame.transform.scale(self.screen, (sw, sh)), (ox, oy))
        off = max(1, round(2 * scale))
        for s, size, color, rect, left, shadow in self.texts:
            px = max(6, round(size * scale))
            f = self._hi_fonts.get(px)
            if f is None:
                f = self._hi_fonts[px] = pygame.font.Font(None, px)
            img = f.render(s, True, color)
            if left:
                r = img.get_rect(topleft=(ox + round(rect.x * scale), oy + round(rect.y * scale)))
            else:
                r = img.get_rect(center=(ox + round(rect.centerx * scale), oy + round(rect.centery * scale)))
            if shadow:
                win.blit(f.render(s, True, (20, 16, 24)), r.move(off, off))
            win.blit(img, r)
        self.texts.clear()

    def popup(self, s, x, y, col):
        self.popups.append([s, x, y, 1.0, col])

    def reset(self):
        self.idle.clear()
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
                self.popup("CRASH!", x, y - 20, (150, 200, 240))
                self.shake = 0.2
            elif kind in ("ward_in", "ward_out"):
                self.fx.burst(x, y + 10, (180, 150, 120), 10, 70, 0.4, 3)
            elif kind == "empty":
                self.popup("empty!", x, y - 26, (230, 230, 230))
            elif kind == "fish":
                self.fx.burst(x, y, (120, 180, 236), 16, 120, 0.6, 3)
                self.popup("+1", x, y - 16, (150, 210, 255))
            elif kind == "chicken":
                self.fx.burst(x, y, (255, 220, 160), 10, 70, 0.5, 2)
            elif kind == "chomp":
                self.fx.burst(x, y, (206, 128, 56), 14, 90, 0.6, 3)
                self.popup("yum!", x, y - 20, (255, 200, 120))
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
                self.popup("There you are!", x, y - 30, PINK)
            elif kind == "helper_in_janis":
                self.fx.burst(x, y, (200, 200, 210), 18, 110, 0.6, 4)
                self.popup("I say!", x, y - 34, (200, 210, 255))
            elif kind == "helper_in_yolanta":
                self.fx.burst(x, y, (220, 200, 240), 18, 110, 0.6, 4)
                self.popup("What was that?!", x, y - 34, PINK)
            elif kind == "grab_janis":
                self.fx.burst(x, y, (120, 140, 220), 16, 110, 0.6, 3)
                self.popup("Gotcha!", x, y - 30, (200, 210, 255))
                self.shake = 0.15
            elif kind == "grab_janis_fox":           # Janis has a soft spot for Walter the fox
                self.fx.burst(x, y - 10, (255, 120, 170), 22, 120, 0.9, 4)
                self.popup("Walter, my boy!", x, y - 32, (255, 150, 190))
                self.shake = 0.15
            elif kind == "grab_yolanta":
                self.fx.burst(x, y, PINK, 16, 110, 0.6, 3)
                self.popup("There you are!", x, y - 30, PINK)
                self.shake = 0.15
            elif kind == "tidy":
                self.fx.burst(x, y, (240, 240, 250), 14, 80, 0.5, 2)
                self.popup("Tidy!", x, y - 30, (230, 230, 240))
            elif kind == "kiss":
                self.fx.burst(x, y - 10, (255, 120, 170), 30, 140, 1.0, 4)
                self.popup("Mwah!", x, y - 34, (255, 140, 190))
            elif kind == "lights_on":
                self.popup("Lights on!", W // 2, 40, (255, 240, 160))
                self.fx.burst(x, y - 20, (255, 240, 160), 20, 120, 0.6, 3)
            elif kind == "hit_fox":
                self.fx.burst(x, y, (232, 52, 72), 24, 170, 0.8, 4)
                self.fx.burst(x, y, (255, 230, 80), 12, 120, 0.6, 3)
                self.popup("-1 heart", x, y - 26, (255, 90, 110))
                self.shake = 0.35
            elif kind.startswith("win_"):
                col = FOX_COL if kind == "win_fox" else CAT_COL
                self.fx.burst(x, y, col, 50, 260, 1.2, 5)
                self.fx.burst(x, y, (255, 255, 255), 30, 200, 1.0, 3)
                self.shake = 0.5

    def draw_body(self, b, key, alpha=None, dt=0.0, closed_eyes=False):
        frames = self.spr[key][b.facing]
        poses = self.spr.get(key + "_pose", {}).get(b.facing)
        bid = id(b)
        idle = self.idle.get(bid, 0.0)
        idle = 0.0 if b.moving else idle + dt
        self.idle[bid] = idle
        phase = (bid % 97) / 97.0                       # so the characters don't blink in sync
        bob = 0
        if b.moving:
            if len(frames) > 2:                         # frame 0 = standing, the rest = walk cycle
                frame = frames[1 + int(b.anim * 10) % (len(frames) - 1)]
            else:
                frame = frames[int(b.anim * 8) % 2]
            bob = -abs(int(math.sin(b.anim * 16) * 2))
        elif poses:
            blink = closed_eyes or (self.t + phase * 3) % 3.4 < 0.14
            if idle > 2.5:                              # sat down after standing for a while
                frame = poses["sit_blink" if blink else "sit"]
            elif (self.t + phase * 5) % 4.0 < 0.35:     # a little tail flick
                frame = poses["tail"]
            else:
                frame = poses["stand_blink" if blink else "stand"]
            if math.sin(self.t * 2.6 + phase * 6) > 0.7:    # breathing
                bob = -1
        else:
            frame = frames[0]
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
        if self.viewer == "cat":                    # online: you only see around yourself
            lights = [] if g.cat.hidden else [(g.cat, 110)]
        elif self.viewer == "fox":
            lights = [(g.fox, 110)]
        else:
            lights = [(g.fox, 110)]
            if not g.cat.hidden:
                lights.append((g.cat, 110))
        lights += [(n, 85 if n.kind == "janis" else 55) for n in g.npcs]
        lights += [(f, 20) for f in g.fish]
        if STYLE["name"] == "manor":
            lights += [(Spot(*cell_center(c, r + 1)), 60) for c, r in manor.fireplaces()]
        steps = 6
        for i in range(steps):
            a = int(base * (steps - 1 - i) / steps)
            for b, rad in lights:
                r = int(rad * (1 - i / steps * 0.6))
                pygame.draw.circle(dark, (5, 5, 15, a), (int(b.x), int(b.y)), r)
        self.screen.blit(dark, (0, HUD_H))

    def draw_game(self, g, m, dt, state):
        self.texts.clear()
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
            draw_fire(scr, self.t, HUD_H)
        for c, r in logic.SWITCHES:                 # light switches on the wall
            sx, sy = c * TILE + 11, (r - 1) * TILE + HUD_H + TILE - 16
            pygame.draw.rect(scr, (60, 50, 50), (sx - 1, sy - 1, 12, 14))
            pygame.draw.rect(scr, (236, 228, 206), (sx, sy, 10, 12))
            pygame.draw.rect(scr, (60, 50, 50), (sx + 4, sy + (7 if g.dark else 2), 2, 4))
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

        # fox dash trail
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
            r = self.draw_body(b, key, alpha, dt, closed_eyes=(key == "fox" and g.fox.kiss > 0))
            if key == "fox":
                if g.fox.stun > 0:
                    self.stars(int(b.x), r.top)
                elif g.fox.kiss > 0:
                    if int(self.t * 6) % 2:
                        self.fx.burst(b.x, b.y - 18, (255, 120, 170), 1, 40, 0.8, 3)
                    bar(scr, int(b.x) - 16, r.top - 8, 32, 5, g.fox.kiss / JANIS_KISS, (255, 120, 170))
                elif g.fox.hold > 0:
                    bar(scr, int(b.x) - 16, r.top - 8, 32, 5, g.fox.hold / JANIS_HOLD, (150, 170, 240))
                    if g.fox.held_by == "janis" and int(self.t * 6) % 2:      # hearts while Janis holds him
                        self.fx.burst(b.x, b.y - 18, (255, 120, 170), 1, 40, 0.8, 3)
                elif g.fox.eat > 0:
                    scr.blit(self.spr["chicken"], self.spr["chicken"].get_rect(midbottom=(int(b.x), r.top)))
                elif g.fox.boost > 0 and int(self.t * 8) % 2:
                    self.fx.burst(b.x, b.y + 6, (255, 200, 120), 1, 30, 0.4, 2)
            if key == "cat" and g.cat.hold > 0:
                total = GRAN_HOLD if g.cat.held_by == "gran" else JANIS_HOLD
                col = (150, 170, 240) if g.cat.held_by == "janis" else PINK
                bar(scr, int(b.x) - 16, r.top - 8, 32, 5, g.cat.hold / total, col)

        if g.cat.hold > 0 and g.cat.held_by in ("gran", "yolanta"):
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
            box = pygame.Rect(W // 2 - 330, H // 2 - 200, 660, 330)
            self.panel(box, (150, 130, 96))
            self.text(f"Round {m.round}", self.f_big, (255, 255, 255), center=(W // 2, box.y + 40))
            self.text(logic.LEVEL["title"], self.f_mid, (236, 222, 190), center=(W // 2, box.y + 80))
            for i, role in enumerate(("cat", "fox")):
                y = box.y + 120 + i * 62
                side = SIDES[m.side_of(role)]
                icon = self.spr["cat_icon" if role == "cat" else "fox_icon"]
                self.screen.blit(icon, icon.get_rect(midleft=(box.x + 40, y + 13)))
                col = CAT_COL if role == "cat" else FOX_COL
                self.text(f"{PLAYER[m.player_of(role)]}  {role.upper()}", self.f_mid, col, topleft=(box.x + 82, y + 1))
                kx = box.x + 330
                r = self.keys(kx, y, side["move"])
                r = self.key(r.right + 14, y, side["names"][1])
                self.key(r.right + 6, y, side["names"][2])
            self.text(str(math.ceil(g.countdown)), self.f_huge, (255, 230, 120), center=(W // 2, box.bottom - 50))
        if g.dark and int(self.t * 2) % 2 and state == "play":
            self.text("LIGHTS OUT!", self.f_mid, (255, 240, 160), center=(W // 2, HUD_H + 20))
        if state == "pause":
            self.overlay()
            self.text("PAUSED", self.f_big, (255, 255, 255), center=(W // 2, H // 2 - 10))
            r = self.key(W // 2 - 130, H // 2 + 28, "P")
            self.text("Resume", self.f_mid, (220, 220, 220), topleft=(r.right + 8, r.y + 2))
            r = self.key(W // 2 + 20, H // 2 + 28, "Esc")
            self.text("Menu", self.f_mid, (220, 220, 220), topleft=(r.right + 8, r.y + 2))
        if state == "over":
            self.draw_round_over(g, m)

    def draw_round_over(self, g, m):
        self.overlay(150)
        msg, col = {
            "caught": ("THE FOX CAUGHT THE CAT!", FOX_COL),
            "wardrobe": ("THE FOX SNIFFED OUT THE CAT!", FOX_COL),
            "time": ("THE CAT GOT AWAY!", CAT_COL),
            "fish": ("THE CAT GOT ALL THE FISH!", CAT_COL),
            "hearts": ("THE BLACK CAT CHASED OFF THE FOX!", CAT_COL),
        }[g.reason]
        cy = H // 2
        self.text(msg, self.f_big, col, center=(W // 2, cy - 70))
        self.text(f"point goes to {PLAYER[m.last]}", self.f_mid, (230, 230, 230), center=(W // 2, cy - 30))
        self.text(f"{PLAYER[0]}   {m.wins[0]} : {m.wins[1]}   {PLAYER[1]}", self.f_big,
                  (255, 255, 255), center=(W // 2, cy + 20))
        if m.done:
            self.text(f"{PLAYER[m.last].upper()} WINS THE MATCH!", self.f_big, (255, 230, 120),
                      center=(W // 2, cy + 75))
            self.hints(W // 2, cy + 105, [("Enter", "New match"), ("Esc", "Menu")])
        else:
            self.text(f"First to {WINS_NEEDED} wins. Roles swap next round.",
                      self.f_small, (210, 210, 210), center=(W // 2, cy + 65))
            self.hints(W // 2, cy + 90, [("Enter", "Next round"), ("Esc", "Menu")])

    def overlay(self, alpha=120):
        o = pygame.Surface((W, H), pygame.SRCALPHA)
        o.fill((10, 8, 14, alpha))
        self.screen.blit(o, (0, 0))

    def key(self, x, y, label, h=26, font=None):
        """Draw a keyboard key (rounded box with its label). Returns its rect."""
        font = font or self.f_small
        scr = self.screen
        arrow = label in ("UP", "DOWN", "LEFT", "RIGHT")
        w = h if (arrow or len(label) == 1) else font.size(label)[0] + 14
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(scr, (20, 16, 24), rect.move(0, 3), border_radius=6)
        pygame.draw.rect(scr, (236, 230, 216), rect, border_radius=6)
        pygame.draw.rect(scr, (150, 140, 128), rect, 1, border_radius=6)
        if arrow:
            cx, cy, k = rect.centerx, rect.centery, h // 4
            pts = {"UP": [(cx, cy - k), (cx - k, cy + k // 2), (cx + k, cy + k // 2)],
                   "DOWN": [(cx, cy + k), (cx - k, cy - k // 2), (cx + k, cy - k // 2)],
                   "LEFT": [(cx - k, cy), (cx + k // 2, cy - k), (cx + k // 2, cy + k)],
                   "RIGHT": [(cx + k, cy), (cx - k // 2, cy - k), (cx - k // 2, cy + k)]}[label]
            pygame.draw.polygon(scr, (44, 38, 46), pts)
        else:
            self.text(label, font, (44, 38, 46), center=rect.center, shadow=False)
        return rect

    def keys(self, x, y, labels, h=26, font=None, gap=4):
        r = None
        for lab in labels:
            r = self.key(x, y, lab, h, font)
            x = r.right + gap
        return r

    def hints(self, cx, y, items, font=None, h=26):
        """A centred row of  [key] label   [key] label ..."""
        font = font or self.f_small
        def kw(k):
            return h if len(k) == 1 or k in ("UP", "DOWN", "LEFT", "RIGHT") else font.size(k)[0] + 14
        total = sum(kw(k) + 8 + font.size(t)[0] for k, t in items) + 34 * (len(items) - 1)
        x = cx - total // 2
        for k, t in items:
            r = self.key(x, y, k, h, font)
            tr = self.text(t, font, (226, 222, 214), topleft=(r.right + 8, y + (h - font.get_height()) // 2 + 1))
            x = tr.right + 34

    def panel(self, rect, accent=(96, 84, 104)):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (22, 18, 26, 228), s.get_rect(), border_radius=14)
        self.screen.blit(s, rect)
        pygame.draw.rect(self.screen, accent, rect, 2, border_radius=14)

    def ability(self, x, y, icon, label, key, cd, total, active=False):
        """Ability badge: icon, label with key, and a cooldown bar."""
        self.screen.blit(icon, icon.get_rect(midleft=(x, y + 8)))
        x += icon.get_width() + 5
        if active:
            self.text(f"{label}: active!", self.f_tiny, (255, 230, 120), topleft=(x, y + 1))
        elif cd <= 0:
            r = self.key(x, y, key, 16, self.f_tiny)
            self.text(label, self.f_tiny, (160, 240, 160), topleft=(r.right + 4, y + 1))
        else:
            self.text(label, self.f_tiny, (150, 140, 160), topleft=(x, y + 1))
            lw = self.f_tiny.size(label)[0]
            bar(self.screen, x + lw + 5, y + 6, 40, 5, 1 - cd / total, (200, 190, 120))

    def draw_hud(self, g, m):
        scr = self.screen
        pygame.draw.rect(scr, (34, 28, 42), (0, 0, W, HUD_H))
        pygame.draw.line(scr, (80, 66, 96), (0, HUD_H - 1), (W, HUD_H - 1), 2)
        cat_side, fox_side = SIDES[m.side_of("cat")]["names"], SIDES[m.side_of("fox")]["names"]

        # cat
        scr.blit(self.spr["cat_icon"], (10, 8))
        r = self.text(f"CAT  {PLAYER[m.cat_player]}", self.f_mid, CAT_COL, topleft=(44, 6))
        for i in range(FISH_WIN):
            scr.blit(self.fish_icon if i < g.fish_got else self.fish_icon_dim, (r.right + 8 + i * 19, 12))
        if g.cat.hidden:
            r = self.text(f"In wardrobe {math.ceil(g.cat.hide_t)}s.  Move: next wardrobe", self.f_tiny, PINK,
                          topleft=(44, 31))
            k = self.key(r.right + 10, 29, cat_side[1], 16, self.f_tiny)
            self.text("get out", self.f_tiny, PINK, topleft=(k.right + 4, 31))
        elif g.cat.hold > 0:
            who = "Janis" if g.cat.held_by == "janis" else "Yolanta"
            self.text(f"{who} has you!", self.f_tiny, PINK, topleft=(44, 31))
        else:
            self.ability(44, 29, self.spr["blackcat_icon"], "black cat", cat_side[2], g.cat.summon_cd,
                         BLACKCAT_COOLDOWN, active=g.npc("blackcat") is not None)
            k = self.key(186, 29, cat_side[1], 16, self.f_tiny)
            if g.cat.ward_cd > 0:
                self.text(f"door, vase  (wardrobe in {math.ceil(g.cat.ward_cd)}s)", self.f_tiny,
                          (150, 140, 160), topleft=(k.right + 4, 31))
            else:
                self.text("door, vase, wardrobe", self.f_tiny, (200, 200, 210), topleft=(k.right + 4, 31))

        # timer
        if g.time_left is None:
            self.text("NO TIMER", self.f_mid, (200, 200, 210), center=(W // 2 + 30, HUD_H // 2 + 2))
        else:
            tl = max(0, math.ceil(g.time_left))
            col = (255, 90, 90) if tl <= 10 else (255, 255, 255)
            self.text(f"{tl // 60}:{tl % 60:02d}", self.f_big, col, center=(W // 2 + 30, HUD_H // 2 + 2))

        # fox
        rx = W - 290
        scr.blit(self.spr["fox_icon"], (rx, 8))
        r = self.text(f"FOX  {PLAYER[1 - m.cat_player]}", self.f_mid, FOX_COL, topleft=(rx + 34, 6))
        for i in range(FOX_HEARTS):
            img = self.spr["heart"] if i < g.fox.hearts else self.spr["heart_empty"]
            scr.blit(img, (r.right + 8 + i * 20, 8))
        if g.fox.stun > 0:
            self.text("stunned!", self.f_tiny, (255, 230, 80), topleft=(rx + 34, 31))
        elif g.fox.kiss > 0:
            self.text("kissed by Janis!", self.f_tiny, (255, 140, 190), topleft=(rx + 34, 31))
        elif g.fox.hold > 0:
            who = "Janis" if g.fox.held_by == "janis" else "Yolanta"
            self.text(f"{who} has you!", self.f_tiny, (170, 190, 255), topleft=(rx + 34, 31))
        elif g.fox.eat > 0:
            self.text("eating chicken...", self.f_tiny, (255, 200, 120), topleft=(rx + 34, 31))
        else:
            self.ability(rx + 34, 29, self.spr["star"], "dash", fox_side[1], g.fox.dash_cd, DASH_COOLDOWN)
            self.ability(rx + 146, 29, self.spr["gran_icon"], "Yolanta", fox_side[2], g.fox.summon_cd,
                         GRAN_COOLDOWN, active=g.perk_active())

    def draw_menu(self, dt):
        self.texts.clear()
        self.t += dt
        scr = self.screen
        scr.blit(self.bg, (0, HUD_H))
        self.overlay(150)
        f = int(self.t * 6) % 2

        def show(key, facing, cx, by, scale=1.0):
            img = self.spr[key][facing][f]
            img = pygame.transform.scale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
            scr.blit(img, img.get_rect(midbottom=(cx, by)))

        # title
        bob = math.sin(self.t * 2) * 3
        r = self.text("BLUE BLOOD", self.f_title, (120, 160, 255), center=(W // 2, 54 + bob))
        pygame.draw.line(scr, (230, 196, 90), (r.left + 10, r.bottom + 2), (r.right - 10, r.bottom + 2), 2)
        self.text("The kitten runs, the fox chases. Roles swap every round. First to 3 wins.",
                  self.f_small, (226, 222, 214), center=(W // 2, 112))

        follow = CONTROLS["follow_role"]

        def role_card(rect, role, title, goal, rows, tips, col):
            self.panel(rect, col)
            show(role, 1 if role == "cat" else -1, rect.x + 62, rect.y + 84, 1.9)
            self.text(title, self.f_big, col, topleft=(rect.x + 120, rect.y + 14))
            self.text(goal, self.f_small, (236, 232, 224), topleft=(rect.x + 122, rect.y + 58))
            side = SIDES[0 if role == "cat" else 1]
            y = rect.y + 100
            for kind, label in rows:
                if kind == "move":
                    k = self.keys(rect.x + 24, y, side["move"]) if follow else \
                        self.key(rect.x + 24, y, "Move")
                else:
                    idx = 1 if kind == "action" else 2
                    k = self.key(rect.x + 24, y, side["names"][idx] if follow else kind.capitalize())
                self.text(label, self.f_small, (236, 232, 224), topleft=(max(k.right, rect.x + 140) + 12, y + 4))
                y += 36
            y += 4
            for tip in tips:
                pygame.draw.circle(scr, col, (rect.x + 30, y + 9), 3)
                self.text(tip, self.f_small, (196, 190, 182), topleft=(rect.x + 44, y))
                y += 25

        cw, ch, top = 556, 318, 136
        role_card(pygame.Rect(W // 2 - cw - 12, top, cw, ch), "cat", "THE KITTEN",
                  ("Collect 5 fish" if SETTINGS["timer"] is None
                   else f"Survive {timer_label(SETTINGS['timer'])} or collect 5 fish"),
                  [("move", "Run"), ("action", "Door, vase or wardrobe"), ("perk", "Call the black cat")],
                  ["Smashed vases slow the fox, but the noise brings help",
                   "Hide in a wardrobe, sneak to another one",
                   "The black cat chases the fox and takes a heart"], CAT_COL)
        role_card(pygame.Rect(W // 2 + 12, top, cw, ch), "fox", "WALTER THE FOX",
                  "Catch the kitten! You have 3 hearts",
                  [("move", "Run"), ("action", "Dash"), ("perk", "Call Yolanta to grab the kitten")],
                  ["Wait at a wardrobe to sniff out the kitten",
                   "Roast chicken makes you faster",
                   "Push against a closed door to scratch through"], FOX_COL)

        # the residents
        strip = pygame.Rect(W // 2 - cw - 12, top + ch + 14, cw * 2 + 24, 64)
        self.panel(strip, (120, 112, 128))
        show("janis", 1, strip.x + 36, strip.bottom - 8, 0.9)
        show("gran", 1, strip.x + 74, strip.bottom - 8, 0.9)
        self.text("Janis and Yolanta wander the house and grab anyone they spot.",
                  self.f_small, (236, 232, 224), topleft=(strip.x + 110, strip.y + 12))
        self.text("Janis adores Walter the fox. When the lights go out, he goes to switch them back on.",
                  self.f_small, (196, 190, 182), topleft=(strip.x + 110, strip.y + 36))

        # controls & settings
        y = strip.bottom + 18
        if not follow:
            self.hints(W // 2, y, [("WASD", "Player 1 moves"), ("E", "action"), ("Q", "perk"),
                                   ("Arrows", "Player 2 moves"), (".", "action"), ("/", "perk")], self.f_tiny, 22)
            y += 30
        style = "Manor" if STYLE["name"] == "manor" else "House"
        keys_mode = "follow the role" if follow else "stay with the player"
        self.hints(W // 2, y, [("R", f"Timer: {timer_label(SETTINGS['timer'])}"), ("T", f"Style: {style}"),
                               ("C", f"Keys {keys_mode}"), ("F11", "Fullscreen")],
                   self.f_small, 24)
        self.hints(W // 2, H - 44, [("Enter", "Play on this computer"), ("O", "Play online")], self.f_mid, 32)

def draw_online(rnd, dt, addr, editing, mode, code, msg):
    """The "Play online" screen."""
    rnd.texts.clear()
    rnd.t += dt
    rnd.screen.blit(rnd.bg, (0, HUD_H))
    rnd.overlay(170)
    box = pygame.Rect(W // 2 - 360, 110, 720, 470)
    rnd.panel(box, (120, 160, 255))
    rnd.text("PLAY ONLINE", rnd.f_big, (120, 160, 255), center=(W // 2, box.y + 46))
    rnd.text("Two computers, one match. Each player sees their own screen.", rnd.f_small,
             (214, 210, 202), center=(W // 2, box.y + 88))
    y = box.y + 130
    rnd.text("Server", rnd.f_small, (180, 176, 170), topleft=(box.x + 50, y + 4))
    field = pygame.Rect(box.x + 140, y, 420, 32)
    pygame.draw.rect(rnd.screen, (40, 34, 46), field, border_radius=6)
    pygame.draw.rect(rnd.screen, (255, 230, 150) if editing else (90, 84, 100), field, 2, border_radius=6)
    caret = "|" if editing and int(rnd.t * 2) % 2 else ""
    rnd.text(addr + caret, rnd.f_small, (240, 236, 228), topleft=(field.x + 10, field.y + 7), shadow=False)
    if not editing:
        k = rnd.key(field.right + 16, y + 3, "A")
        rnd.text("change", rnd.f_tiny, (180, 176, 170), topleft=(k.right + 6, y + 8))
    y += 70
    if mode == "join":
        rnd.text("Type the room code your friend got:", rnd.f_mid, (236, 232, 224), center=(W // 2, y + 10))
        cf = pygame.Rect(W // 2 - 110, y + 40, 220, 64)
        pygame.draw.rect(rnd.screen, (40, 34, 46), cf, border_radius=10)
        pygame.draw.rect(rnd.screen, (255, 230, 150), cf, 2, border_radius=10)
        rnd.text((code + ("_" if int(rnd.t * 2) % 2 else " ")).ljust(4), rnd.f_big, (255, 236, 170),
                 center=cf.center, shadow=False)
        rnd.hints(W // 2, y + 130, [("Enter", "Join"), ("Esc", "Back")])
    elif editing:
        rnd.text("Type the server address (an IP like 192.168.1.20, or a web address),", rnd.f_small,
                 (214, 210, 202), center=(W // 2, y + 10))
        rnd.text("then press Enter.", rnd.f_small, (214, 210, 202), center=(W // 2, y + 36))
        rnd.hints(W // 2, y + 80, [("Enter", "Save"), ("Esc", "Cancel")])
    else:
        r = rnd.key(box.x + 120, y, "H", 34, rnd.f_mid)
        rnd.text("Host a game", rnd.f_mid, (236, 232, 224), topleft=(r.right + 14, y + 4))
        rnd.text("You get a room code to send to your friend", rnd.f_small, (180, 176, 170),
                 topleft=(r.right + 14, y + 36))
        y += 86
        r = rnd.key(box.x + 120, y, "J", 34, rnd.f_mid)
        rnd.text("Join a game", rnd.f_mid, (236, 232, 224), topleft=(r.right + 14, y + 4))
        rnd.text("Type the code your friend got", rnd.f_small, (180, 176, 170), topleft=(r.right + 14, y + 36))
        y += 96
        rnd.text(f"Round timer: {timer_label(SETTINGS['timer'])}  (the host's setting, change it with R in the menu)",
                 rnd.f_tiny, (170, 166, 160), center=(W // 2, y))
        rnd.hints(W // 2, box.bottom - 46, [("Esc", "Back to the menu")])
    if msg:
        rnd.text(msg, rnd.f_small, (255, 140, 130), center=(W // 2, box.bottom + 30))


def draw_waiting(rnd, dt, client):
    rnd.texts.clear()
    rnd.t += dt
    rnd.screen.blit(rnd.bg, (0, HUD_H))
    rnd.overlay(170)
    box = pygame.Rect(W // 2 - 330, 150, 660, 380)
    rnd.panel(box, (120, 160, 255))
    if client.status == "error":
        rnd.text("Something went wrong", rnd.f_big, (255, 150, 140), center=(W // 2, box.y + 70))
        rnd.text(client.error or "", rnd.f_small, (236, 232, 224), center=(W // 2, box.y + 140))
        rnd.text("Check the server address and that the server is running.", rnd.f_small,
                 (180, 176, 170), center=(W // 2, box.y + 175))
    elif client.code:
        rnd.text("Room code", rnd.f_mid, (214, 210, 202), center=(W // 2, box.y + 60))
        rnd.text(client.code, rnd.f_huge, (255, 236, 170), center=(W // 2, box.y + 140))
        rnd.text("Send this code to your friend. They choose Join and type it.", rnd.f_small,
                 (236, 232, 224), center=(W // 2, box.y + 220))
        dots = "." * (1 + int(rnd.t * 2) % 3)
        rnd.text("Waiting for the second player" + dots, rnd.f_small, (180, 176, 170), center=(W // 2, box.y + 256))
    else:
        dots = "." * (1 + int(rnd.t * 2) % 3)
        rnd.text("Connecting" + dots, rnd.f_big, (236, 232, 224), center=(W // 2, box.y + 150))
        rnd.text(client.url, rnd.f_small, (180, 176, 170), center=(W // 2, box.y + 210))
    rnd.hints(W // 2, box.bottom - 50, [("Esc", "Cancel")])


def make_window(fullscreen):
    if sys.platform == "emscripten":              # browser build
        return pygame.display.set_mode((W, H))
    if fullscreen:                                # the real screen resolution
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    return pygame.display.set_mode((W, H), pygame.RESIZABLE)


def dpi_aware():
    """On Windows with display scaling (125%, 150%...) stop the system from blurring the window."""
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


async def main():
    dpi_aware()
    pygame.init()
    pygame.display.set_caption("Blue Blood")
    fullscreen = True
    screen = make_window(fullscreen)
    clock = pygame.time.Clock()
    rnd = Renderer(screen)
    game = Game()
    match = Match()
    state = "menu"
    held = set()   # physical keys currently held down
    # online
    client = None
    mirror = None
    addr, editing, mode, code, msg = load_server(), False, None, "", ""
    addr_backup = addr
    last_sent, send_timer, net_round = None, 0.0, None

    while True:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        keys_down = set()
        typed = ""
        for e in pygame.event.get():
            if e.type == pygame.TEXTINPUT:
                typed += e.text
            if e.type == pygame.QUIT:
                pygame.quit()
                return
            if e.type == pygame.KEYDOWN:
                if e.scancode == pygame.KSCAN_F11 and sys.platform != "emscripten":
                    fullscreen = not fullscreen
                    rnd.window = make_window(fullscreen)
                keys_down.add(e.scancode)
                held.add(e.scancode)
            elif e.type == pygame.KEYUP:
                held.discard(e.scancode)
            elif e.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
                held.clear()

        if state == "menu":
            if pygame.KSCAN_O in keys_down:
                state, editing, mode, code, msg = "online", False, None, "", ""
                typed = ""
            if pygame.KSCAN_R in keys_down:
                SETTINGS["timer"] = TIMERS[(TIMERS.index(SETTINGS["timer"]) + 1) % len(TIMERS)]
            if pygame.KSCAN_C in keys_down:
                CONTROLS["follow_role"] = not CONTROLS["follow_role"]
            if pygame.KSCAN_T in keys_down:
                STYLE["name"] = "classic" if STYLE["name"] == "manor" else "manor"
            if pygame.KSCAN_RETURN in keys_down:
                match = Match()
                game = Game(level=match.level, round_time=SETTINGS["timer"])
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
        elif state == "online":
            if editing:
                if pygame.KSCAN_BACKSPACE in keys_down:
                    addr = addr[:-1]
                addr += "".join(ch for ch in typed if ch.isprintable() and ch != " ")
                if pygame.KSCAN_RETURN in keys_down and addr:
                    editing = False
                    save_server(addr)
                elif pygame.KSCAN_ESCAPE in keys_down:
                    editing, addr = False, addr_backup
            elif mode == "join":
                if pygame.KSCAN_BACKSPACE in keys_down:
                    code = code[:-1]
                code = (code + "".join(ch for ch in typed.upper() if ch.isalpha()))[:4]
                if pygame.KSCAN_RETURN in keys_down and len(code) == 4:
                    client = NetClient(addr)
                    client.send({"type": "join", "code": code})
                    state, mirror, net_round = "net", None, None
                elif pygame.KSCAN_ESCAPE in keys_down:
                    mode = None
            else:
                if pygame.KSCAN_A in keys_down:
                    editing, addr_backup, msg = True, addr, ""
                elif pygame.KSCAN_J in keys_down:
                    mode, code, msg = "join", "", ""
                elif pygame.KSCAN_H in keys_down:
                    client = NetClient(addr)
                    client.send({"type": "host", "timer": SETTINGS["timer"]})
                    state, mirror, net_round = "net", None, None
                elif pygame.KSCAN_ESCAPE in keys_down:
                    state = "menu"
            if state == "online":
                draw_online(rnd, dt, addr, editing, mode, code, msg)
        elif state == "net":
            leave = pygame.KSCAN_ESCAPE in keys_down
            if client.snap is None or client.meta is None:
                draw_waiting(rnd, dt, client)
                if client.status == "error" and client.error == "No game with this code":
                    msg = "No game with this code. Check it and try again."
                    leave = True
                    state = "online"
            else:
                meta = client.meta
                if mirror is None:
                    mirror = net.MirrorGame(client.snap["lvl"])
                if meta["round"] != net_round:
                    net_round = meta["round"]
                    rnd.reset()
                mirror.apply(client.snap)
                mirror.events = client.take_events()
                rnd.handle_events(mirror)
                mirror.smooth(dt)
                you = meta["you"]
                PLAYER[:] = ["You", "Friend"] if you == 0 else ["Friend", "You"]
                rnd.viewer = "cat" if meta["cat_player"] == you else "fox"
                if meta["state"] == "play":
                    inp = online_input(held, keys_down)
                    send_timer -= dt
                    if inp["act"] or inp["summon"] or (inp["dx"], inp["dy"]) != last_sent or send_timer <= 0:
                        client.send(dict(inp, type="input"))
                        last_sent, send_timer = (inp["dx"], inp["dy"]), 0.25
                elif pygame.KSCAN_RETURN in keys_down:
                    client.send({"type": "next"})
                view = "play" if meta["state"] == "play" else "over"
                rnd.draw_game(mirror, NetMatch(meta), dt, view)
                if client.status in ("left", "error", "closed"):
                    rnd.overlay(150)
                    text = "Your friend left the game." if client.status == "left" else \
                        (client.error or "The connection was closed.")
                    rnd.text(text, rnd.f_big, (255, 236, 170), center=(W // 2, H // 2 - 20))
                    rnd.hints(W // 2, H // 2 + 40, [("Esc", "Back to the menu")])
            if leave and state == "net":
                client.close()
                client, mirror = None, None
                PLAYER[:] = ["Player 1", "Player 2"]
                rnd.viewer = None
                state = "menu"
            elif leave:
                client.close()
                client, mirror = None, None
        elif state == "over":
            if pygame.KSCAN_RETURN in keys_down:
                if match.done:
                    match = Match()
                else:
                    match.next_round()
                game.new_round(match.level)
                rnd.reset()
                state = "play"
            elif pygame.KSCAN_ESCAPE in keys_down:
                state = "menu"
            rnd.draw_game(game, match, dt, state)

        rnd.present()
        pygame.display.flip()
        await asyncio.sleep(0)  # required for the browser build (pygbag)


if __name__ == "__main__":
    asyncio.run(main())
