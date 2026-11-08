"""Online play: what the server sends to each player, and the player's copy of the round.

No pygame here, so the server can use it too.
"""
import math

import logic
from logic import Game, Item, Npc, Shards

PORT = 8765

CAT_KEYS = ("hidden", "hold", "held_by", "summon_cd", "ward_cd", "hide_t")
FOX_KEYS = ("stun", "kiss", "eat", "boost", "dash_t", "dash_cd", "summon_cd", "hearts", "hold", "held_by")
NPC_KEYS = ("kind", "life", "holding", "mode")


def _body(b, keys):
    d = {"x": round(b.x, 1), "y": round(b.y, 1), "f": b.facing, "m": b.moving, "a": round(b.anim, 3)}
    for k in keys:
        v = getattr(b, k, None)
        d[k] = round(v, 2) if isinstance(v, float) else v
    return d


def snapshot(g, viewer):
    """The state of the round as one player ("cat" or "fox") is allowed to see it."""
    cat = _body(g.cat, CAT_KEYS)
    if viewer == "fox" and g.cat.hidden:       # the fox must not know which wardrobe the kitten is in
        cat["x"] = cat["y"] = -999
    return {
        "lvl": g.level,
        "cat": cat,
        "fox": _body(g.fox, FOX_KEYS),
        "npcs": [_body(n, NPC_KEYS) for n in g.npcs],
        "doors": [[c, r, d.open, round(d.scratch, 2)] for (c, r), d in g.doors.items()],
        "vases": [v.broken for v in g.vases],
        "shards": [[s.c, s.r, round(s.life, 1)] for s in g.shards],
        "fish": [[f.x, f.y] for f in g.fish],
        "chicken": [g.chicken.x, g.chicken.y] if g.chicken else None,
        "sniff": [round(w.sniff, 2) for w in g.wardrobes],
        "time": None if g.time_left is None else round(g.time_left, 2),
        "cd": round(g.countdown, 2),
        "el": round(g.elapsed, 2),
        "dark": g.dark,
        "warn": g.dark_warning,
        "fishgot": g.fish_got,
        "win": g.winner,
        "reason": g.reason,
        "ev": [list(e) for e in g.events],
    }


class MirrorGame(Game):
    """A player's copy of the round, filled in from the server. It is never simulated locally."""

    def __init__(self, level):
        super().__init__(seed=0, level=level, round_time=None)
        self.npcs = []
        self._dark = self._warn = False

    @property
    def dark(self):
        return self._dark

    @property
    def dark_warning(self):
        return self._warn

    def step(self, dt, inp):
        pass

    @staticmethod
    def _set_body(b, d, keys):
        b.tx, b.ty = d["x"], d["y"]
        if not getattr(b, "_placed", False):
            b.x, b.y, b._placed = d["x"], d["y"], True
        b.facing, b.moving, b.anim = d["f"], d["m"], d["a"]
        for k in keys:
            setattr(b, k, d[k])

    def apply(self, s):
        if s["lvl"] != self.level:
            self.new_round(s["lvl"])
            self.npcs = []
        self._set_body(self.cat, s["cat"], CAT_KEYS)
        self._set_body(self.fox, s["fox"], FOX_KEYS)
        old = {n.kind: n for n in self.npcs}
        npcs = []
        for d in s["npcs"]:
            n = old.get(d["kind"]) or Npc(d["kind"], d["x"], d["y"], 0, 0)
            self._set_body(n, d, NPC_KEYS)
            npcs.append(n)
        self.npcs = npcs
        for c, r, is_open, scratch in s["doors"]:
            d = self.doors[(c, r)]
            d.open, d.scratch = is_open, scratch
        for v, broken in zip(self.vases, s["vases"]):
            v.broken = broken
        self.shards = []
        for c, r, life in s["shards"]:
            sh = Shards(c, r)
            sh.life = life
            self.shards.append(sh)
        self.fish = [Item(x, y) for x, y in s["fish"]]
        self.chicken = Item(*s["chicken"]) if s["chicken"] else None
        for w, sn in zip(self.wardrobes, s["sniff"]):
            w.sniff = sn
        self.time_left, self.countdown, self.elapsed = s["time"], s["cd"], s["el"]
        self._dark, self._warn = s["dark"], s["warn"]
        self.fish_got, self.winner, self.reason = s["fishgot"], s["win"], s["reason"]

    def smooth(self, dt):
        """Glide everyone towards where the server last saw them (30 updates/s -> smooth 60 fps)."""
        k = min(1.0, dt * 18)
        for b in [self.cat, self.fox] + self.npcs:
            if not hasattr(b, "tx"):
                continue
            if math.hypot(b.tx - b.x, b.ty - b.y) > 64:     # a jump (wardrobe, summon): no gliding
                b.x, b.y = b.tx, b.ty
            else:
                b.x += (b.tx - b.x) * k
                b.y += (b.ty - b.y) * k


def level_title(name):
    return logic.LEVELS[name]["title"]
