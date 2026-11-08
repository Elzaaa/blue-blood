"""Game logic: the cat runs, the fox chases.

No pygame here: only the rules and the state of a single round.
The same code can later run on an online server.
"""
import math
import random
from collections import deque

TILE = 32

# --- locations ------------------------------------------------------------
# The maps live in levels.py. use_level() switches the current one; the rest of
# the code reads MAP, ROOMS, SWITCHES etc. from this module.
import levels  # noqa: E402
from levels import COLS, ROWS, LEVELS  # noqa: E402,F401

SOLID_TILES = levels.SOLID
LEVEL = MAP = ROOMS = KITCHEN = CAT_SPAWN = FOX_SPAWN = SWITCHES = None


def room_of(c, r):
    """Which room a cell belongs to (doors and walls take the room next to them)."""
    for dc, dr in ((0, 0), (0, 1), (1, 0), (-1, 0), (0, -1)):
        for name, c0, r0, c1, r1 in ROOMS:
            if c0 <= c + dc <= c1 and r0 <= r + dr <= r1:
                return name
    return ROOMS[0][0]


def use_level(name):
    global LEVEL, MAP, ROOMS, KITCHEN, CAT_SPAWN, FOX_SPAWN, SWITCHES
    LEVEL = LEVELS[name]
    MAP = LEVEL["map"]
    ROOMS = LEVEL["rooms"]
    CAT_SPAWN = LEVEL["cat_spawn"]
    FOX_SPAWN = LEVEL["fox_spawn"]
    SWITCHES = LEVEL["switches"]
    # KITCHEN = where the fox's snack (the roast chicken) shows up on this level
    KITCHEN = [(c, r) for r in range(ROWS) for c in range(COLS)
               if MAP[r][c] == "." and room_of(c, r) == LEVEL["food_room"]]


use_level("ground")

# --- balance ------------------------------------------------------------
ROUND_TIME = 90.0        # the cat must survive this long...
FISH_WIN = 5             # ...or collect this many fish
FISH_ON_MAP = 2
FISH_RESPAWN = 2.5
PICK_DIST = 20

COUNTDOWN = 3.0
HALF = 9                 # half the hitbox size (px)
CAT_SPEED = 150
FOX_SPEED = 165
CATCH_DIST = 22

ACT_REACH = 50           # reach for a door / vase / wardrobe
ACT_COOLDOWN = 0.35

VASE_REACH = 46
SHARD_LIFE = 15.0
SHARD_SLOW = 0.5         # fox speed on shards

WARD_MAX = 6.0           # max time inside a wardrobe
WARD_TRAVEL = 0.8        # moving to another wardrobe
WARD_COOLDOWN = 6.0
SNIFF_TIME = 0.7
SNIFF_DIST = 24

DASH_MULT = 2.2          # fox dash
DASH_TIME = 0.28
DASH_COOLDOWN = 4.0
SCRATCH_TIME = 1.3       # fox scratching through a closed door

CHICKEN_FIRST = 8.0
CHICKEN_RESPAWN = 15.0
CHICKEN_EAT = 1.2
CHICKEN_BOOST = 6.0
CHICKEN_MULT = 1.3

FIRST_BLACKOUT = (18.0, 32.0)   # the lights first go out at a random moment in this window...
BLACKOUT_GAP = (22.0, 38.0)     # ...and then again after this much light (twice in a 1:30 round)
NO_TIMER_LENGTH = 1800.0        # blackouts are planned this far ahead when there's no timer
DARK_TIME = 12.0
DARK_MIN = 5.0           # Janis can't switch the lights back on sooner than this
DARK_WARN = 1.5

# Janis and Yolanta live in the house: each strolls around their own part of it and goes
# after anyone they spot. Janis has an eye for the fox (Walter), Yolanta for the kitten.
RES_PATROL_SPEED = 52
RES_CHASE_SPEED = {"janis": 84, "yolanta": 96}
RES_NOTICE = {"janis": {"fox": 170, "cat": 90}, "yolanta": {"cat": 170, "fox": 90}}
RES_LOSE = 1.5           # keeps going where they last saw someone for this long
RES_IGNORE = 6.0         # after letting someone go they leave them alone for a while
RES_PAUSE = (1.0, 3.0)   # little stops while strolling

JANIS_SPEED = 72         # Janis walking to the light switch
JANIS_DELAY = 2.0        # he notices the blackout a moment later
JANIS_NOTICE = 110       # while busy, they only grab someone who comes this close
JANIS_REACH = 24
JANIS_HOLD = 2.0
JANIS_KISS_CHANCE = 0.2  # 1 in 5: kisses the fox instead of grabbing it
JANIS_KISS = 3.0         # the kissed fox is too flustered to move

VASE_DELAY = 2.5         # a smashed vase is loud: Janis or Yolanta always come to check

CARRIER_AFTER = 3        # every 3rd time Janis catches Walter, it's the pet carrier
CARRIER_TIME = 8.0       # let out after this long anyway...
CARRIER_TAPS = 12        # ...or sooner by tapping the action key this many times

BEDS = 2                 # comfy pet beds per round: step on one and you doze off
SLEEP_TIME = 3.5
BED_REST = 12.0          # a bed that was just slept in stays empty for a while

FOX_HEARTS = 3
SUMMON_FIRST = 6.0

BLACKCAT_SPEED = 140     # black cat (cat perk)
BLACKCAT_LIFE = 8.0
BLACKCAT_COOLDOWN = 18.0
BLACKCAT_REACH = 26
FOX_HIT_STUN = 1.5

GRAN_SPEED = 105         # Yolanta answering the fox's call (fox perk)
GRAN_LIFE = 10.0
GRAN_COOLDOWN = 18.0
GRAN_REACH = 24
GRAN_HOLD = 2.5

NPC_DOOR_TIME = 0.6


def cell_center(c, r):
    return ((c + 0.5) * TILE, (r + 0.5) * TILE)


def cell_of(b):
    return (int(b.x // TILE), int(b.y // TILE))


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def dist_to(b, x, y):
    return math.hypot(b.x - x, b.y - y)


def is_floor(c, r):
    return 0 <= c < COLS and 0 <= r < ROWS and MAP[r][c] in ".,"


class Door:
    def __init__(self, c, r):
        self.c, self.r = c, r
        self.open = True
        self.scratch = 0.0
        self.scratching = False
        self.horizontal = MAP[r][c - 1] == "#"

    @property
    def center(self):
        return cell_center(self.c, self.r)


class Wardrobe:
    def __init__(self, c, r):
        self.c, self.r = c, r
        self.front = next((c + dc, r + dr) for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0))
                          if is_floor(c + dc, r + dr))
        self.sniff = 0.0
        self.cool = 0.0

    @property
    def center(self):
        return cell_center(self.c, self.r)


class Vase:
    def __init__(self, c, r):
        self.c, self.r = c, r
        self.broken = False

    @property
    def center(self):
        return cell_center(self.c, self.r)


class Bed:
    def __init__(self, c, r):
        self.c, self.r = c, r
        self.cool = 0.0

    @property
    def center(self):
        return cell_center(self.c, self.r)


class Item:
    def __init__(self, x, y):
        self.x, self.y = x, y


class Shards:
    def __init__(self, c, r):
        self.c, self.r = c, r
        self.life = SHARD_LIFE


class Body:
    def __init__(self, x, y, speed):
        self.x, self.y = x, y
        self.speed = speed
        self.facing = 1
        self.moving = False
        self.anim = 0.0


class Npc(Body):
    def __init__(self, kind, x, y, speed, life):
        super().__init__(x, y, speed)
        self.kind = kind          # "blackcat" (cat perk), "janis", "yolanta" (the residents)
        self.life = life
        self.door_t = 0.0
        self.holding = 0.0
        self.goal = None
        self.goal_cell = None
        self.mode = None
        self.blackout = None
        self.victim = None
        self.ignore = {"cat": 0.0, "fox": 0.0}
        self.pause = 0.0
        self.target = None
        self.lost = 0.0
        self.perk_t = 0.0
        self.carrying = False     # Janis carrying Walter to the pet carrier


class Game:
    def __init__(self, seed=None, level=None, round_time=ROUND_TIME):
        """round_time: seconds the cat must survive, or None for no timer."""
        self.rng = random.Random(seed)
        self.round_time = round_time
        self.new_round(level)

    # ------------------------------------------------------------------
    def new_round(self, level=None):
        if level:
            use_level(level)
        self.level = LEVEL["name"]
        self.doors, self.wardrobes, self.vases = {}, [], []
        for r, row in enumerate(MAP):
            for c, ch in enumerate(row):
                if ch == "D":
                    self.doors[(c, r)] = Door(c, r)
                elif ch == "w":
                    self.wardrobes.append(Wardrobe(c, r))
                elif ch == "v":
                    self.vases.append(Vase(c, r))

        cat = self.cat = Body(*cell_center(*CAT_SPAWN), CAT_SPEED)
        cat.act_cd = 0.0
        cat.hold = 0.0
        cat.summon_cd = SUMMON_FIRST
        cat.hidden = False
        cat.ward = None
        cat.travel = 0.0
        cat.travel_to = None
        cat.hide_t = 0.0
        cat.ward_cd = 0.0
        cat.last_dir = (0, 0)
        cat.held_by = None
        cat.sleep = 0.0

        fox = self.fox = Body(*cell_center(*FOX_SPAWN), FOX_SPEED)
        fox.dash_t = 0.0
        fox.dash_cd = 0.0
        fox.stun = 0.0
        fox.hearts = FOX_HEARTS
        fox.summon_cd = SUMMON_FIRST
        fox.eat = 0.0
        fox.hold = 0.0
        fox.kiss = 0.0
        fox.held_by = None
        fox.cage = 0.0
        fox.cage_taps = 0
        fox.sleep = 0.0
        fox.boost = 0.0

        self.npcs = [self._make_resident("janis"), self._make_resident("yolanta")]
        self.fish = []
        self.fish_got = 0
        self.fish_timer = 0.0
        for _ in range(FISH_ON_MAP):
            self._spawn_fish()
        self.chicken = None
        self.chicken_timer = CHICKEN_FIRST
        self.shards = []
        self.beds = self._place_beds()
        self.janis_catches = 0       # Walter's misdeeds: every 3rd catch -> the carrier
        self.pending = []        # vase noise: [time, shard cell] -> someone comes to check

        self.time_left = self.round_time      # None = no timer
        self.elapsed = 0.0
        self.blackouts = []
        limit = (self.round_time - 10) if self.round_time else NO_TIMER_LENGTH
        start = self.rng.uniform(*FIRST_BLACKOUT)
        while start < limit:
            self.blackouts.append([start, start + DARK_TIME])
            start += DARK_TIME + self.rng.uniform(*BLACKOUT_GAP)
        self.countdown = COUNTDOWN
        self.winner = None
        self.reason = None       # caught | wardrobe | time | fish | hearts
        self.events = []         # for effects and sounds: (kind, x, y)

    def npc(self, kind):
        return next((n for n in self.npcs if n.kind == kind), None)

    @property
    def dark(self):
        return any(a <= self.elapsed < b for a, b in self.blackouts)

    @property
    def dark_warning(self):
        return any(a - DARK_WARN <= self.elapsed < a for a, _ in self.blackouts)

    def perk_active(self):
        y = self.npc("yolanta")
        return y is not None and y.mode == "perk"

    def fox_free(self):
        f = self.fox
        return f.stun <= 0 and f.hold <= 0 and f.kiss <= 0 and f.cage <= 0 and f.sleep <= 0

    # --- map and collisions -------------------------------------------
    def solid(self, c, r):
        if not (0 <= c < COLS and 0 <= r < ROWS):
            return True
        ch = MAP[r][c]
        if ch in SOLID_TILES:
            return True
        if ch == "D":
            return not self.doors[(c, r)].open
        return False

    def walkable(self, c, r):
        """For pathfinding: doors count as passable (helpers open them)."""
        return 0 <= c < COLS and 0 <= r < ROWS and MAP[r][c] not in SOLID_TILES

    def _hits(self, x, y):
        c0, c1 = int((x - HALF) // TILE), int((x + HALF - 0.001) // TILE)
        r0, r1 = int((y - HALF) // TILE), int((y + HALF - 0.001) // TILE)
        return [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                if self.solid(c, r)]

    def _move_axis(self, p, dx, dy):
        if dx:
            nx = p.x + dx
            hits = self._hits(nx, p.y)
            if hits:
                if dx > 0:
                    nx = min(c for c, _ in hits) * TILE - HALF - 0.01
                else:
                    nx = (max(c for c, _ in hits) + 1) * TILE + HALF + 0.01
            p.x = nx
            return hits
        if dy:
            ny = p.y + dy
            hits = self._hits(p.x, ny)
            if hits:
                if dy > 0:
                    ny = min(r for _, r in hits) * TILE - HALF - 0.01
                else:
                    ny = (max(r for _, r in hits) + 1) * TILE + HALF + 0.01
            p.y = ny
            return hits
        return []

    def _move(self, p, mx, my, speed, dt):
        """Movement with walls + nudging into doorways."""
        blocked = []
        step = speed * dt
        hx = self._move_axis(p, mx * step, 0)
        blocked += hx
        if hx and my == 0:
            ahead = int((p.x + math.copysign(HALF + 2, mx)) // TILE)
            row = int(p.y // TILE)
            if not self.solid(ahead, row):
                diff = (row + 0.5) * TILE - p.y
                self._move_axis(p, 0, math.copysign(min(abs(diff), step), diff))
        hy = self._move_axis(p, 0, my * step)
        blocked += hy
        if hy and mx == 0:
            ahead = int((p.y + math.copysign(HALF + 2, my)) // TILE)
            col = int(p.x // TILE)
            if not self.solid(col, ahead):
                diff = (col + 0.5) * TILE - p.x
                self._move_axis(p, math.copysign(min(abs(diff), step), diff), 0)
        p.moving = bool(mx or my)
        p.anim_rate = speed / p.speed if p.speed else 1.0   # legs move faster when running faster
        if mx:
            p.facing = 1 if mx > 0 else -1
        return blocked

    @staticmethod
    def _norm(dx, dy):
        l = math.hypot(dx, dy)
        return (dx / l, dy / l) if l > 0.001 else (0.0, 0.0)

    def _overlaps_tile(self, p, c, r):
        return (p.x + HALF > c * TILE and p.x - HALF < (c + 1) * TILE and
                p.y + HALF > r * TILE and p.y - HALF < (r + 1) * TILE)

    # --- pathfinding ---------------------------------------------------
    def _bfs(self, start, goal=None):
        dist_map, parent = {start: 0}, {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur == goal:
                break
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (cur[0] + dc, cur[1] + dr)
                if n not in dist_map and self.walkable(*n):
                    dist_map[n] = dist_map[cur] + 1
                    parent[n] = cur
                    q.append(n)
        return dist_map, parent

    def _next_cell(self, start, goal):
        if start == goal:
            return None
        _, parent = self._bfs(start, goal)
        if goal not in parent:
            return None
        cur = goal
        while parent[cur] != start:
            cur = parent[cur]
        return cur

    def _chase(self, n, target, dt):
        start, goal = cell_of(n), cell_of(target)
        nxt = self._next_cell(start, goal)
        if nxt is None:
            tx, ty = target.x, target.y
        else:
            cx, cy = cell_center(*start)
            nx, ny = cell_center(*nxt)
            tx, ty = (nx, cy) if nxt[0] != start[0] else (cx, ny)
        mx, my = self._norm(tx - n.x, ty - n.y)
        blocked = self._move(n, mx, my, n.speed, dt)
        closed = [self.doors[c] for c in blocked if c in self.doors and not self.doors[c].open]
        if closed:
            n.door_t += dt
            if n.door_t >= NPC_DOOR_TIME:
                closed[0].open = True
                n.door_t = 0
                self.events.append(("open", *closed[0].center))
        else:
            n.door_t = 0

    # --- item spawning ------------------------------------------------
    def _spawn_fish(self):
        dist_map, _ = self._bfs(cell_of(self.cat))
        taken = {cell_of(f) for f in self.fish}
        cands = [c for c, d in dist_map.items() if d >= 8 and is_floor(*c) and c not in taken]
        if cands:
            self.fish.append(Item(*cell_center(*self.rng.choice(cands))))

    def _gran_spawn(self):
        """Grandma appears somewhere near the cat (4-7 cells away)."""
        dist_map, _ = self._bfs(cell_of(self.cat))
        cands = [c for c, d in dist_map.items() if 4 <= d <= 7 and is_floor(*c)]
        if not cands:
            cands = [c for c, d in dist_map.items() if d >= 2 and is_floor(*c)]
        return cell_center(*self.rng.choice(cands))

    # --- game step ----------------------------------------------------
    def step(self, dt, inp):
        """inp = {'cat': {'dx','dy','act','summon'}, 'fox': {'dx','dy','act','summon'}}"""
        self.events = []
        if self.winner:
            return
        if self.countdown > 0:
            self.countdown -= dt
            return

        self.elapsed += dt
        if self.time_left is not None:
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self._win("cat", "time")
                return
        for bo in self.blackouts:
            if bo[0] <= self.elapsed < bo[0] + dt:
                self.events.append(("lights_off", 0, 0))
            t = bo[0] + JANIS_DELAY
            if t <= self.elapsed < t + dt and self.elapsed < bo[1]:
                self._spawn_janis(bo)

        for p in list(self.pending):
            if self.elapsed >= p[0]:
                self.pending.remove(p)
                if any((s.c, s.r) == p[1] for s in self.shards) and not self._vase_responder(p[1]):
                    self.pending.append([self.elapsed + 0.5, p[1]])     # both busy: whoever is free first comes

        self._update_cat(dt, inp["cat"])
        self._update_fox(dt, inp["fox"])
        self._update_doors(dt)
        self._update_items(dt)
        if not self.winner:
            self._update_wardrobes(dt)
        if not self.winner:
            self._update_npcs(dt)
        if self.winner:
            return

        for b in [self.cat, self.fox] + self.npcs:
            if b.moving:
                b.anim += dt * getattr(b, "anim_rate", 1.0)

        cat, fox = self.cat, self.fox
        if not cat.hidden and self.fox_free() and dist(cat, fox) < CATCH_DIST:
            self._win("fox", "caught")

    # --- cat ------------------------------------------------------------
    def _update_cat(self, dt, ci):
        cat = self.cat
        cat.act_cd = max(0.0, cat.act_cd - dt)
        cat.summon_cd = max(0.0, cat.summon_cd - dt)
        cat.ward_cd = max(0.0, cat.ward_cd - dt)
        d = (ci.get("dx", 0), ci.get("dy", 0))
        new_dir = d != (0, 0) and d != cat.last_dir
        cat.last_dir = d

        if cat.hidden:
            cat.moving = False
            if cat.travel > 0:
                cat.travel -= dt
                if cat.travel <= 0:
                    cat.ward = cat.travel_to
                    cat.travel_to = None
                    cat.x, cat.y = cell_center(*cat.ward.front)
                return
            cat.hide_t -= dt
            if (ci.get("act") and cat.act_cd <= 0) or cat.hide_t <= 0:
                self._exit_wardrobe()
            elif new_dir:
                self._travel(*d)
            return

        if cat.sleep > 0:
            cat.sleep -= dt
            cat.moving = False
            return
        if cat.hold > 0:
            cat.hold -= dt
            cat.moving = False
            return
        mx, my = self._norm(*d)
        self._move(cat, mx, my, cat.speed, dt)
        if ci.get("act") and cat.act_cd <= 0:
            self._cat_action()
        if ci.get("summon") and cat.summon_cd <= 0 and not self.npc("blackcat"):
            self.npcs.append(Npc("blackcat", cat.x, cat.y, BLACKCAT_SPEED, BLACKCAT_LIFE))
            cat.summon_cd = BLACKCAT_COOLDOWN
            self.events.append(("summon_blackcat", cat.x, cat.y))

    def _cat_action(self):
        """One button: door, vase or wardrobe, whichever is closest."""
        cat = self.cat
        cands = []
        for d in self.doors.values():
            # +6 px: when a door and a vase/wardrobe are equally close, the vase/wardrobe wins
            cands.append((dist_to(cat, *d.center) + 6, "door", d))
        for v in self.vases:
            if not v.broken:
                cands.append((dist_to(cat, *v.center), "vase", v))
        if cat.ward_cd <= 0:
            for w in self.wardrobes:
                cands.append((dist_to(cat, *w.center), "ward", w))
        cands = [c for c in cands if c[0] < ACT_REACH]
        if not cands:
            return
        _, kind, obj = min(cands, key=lambda c: c[0])
        cat.act_cd = ACT_COOLDOWN
        if kind == "door":
            self._toggle_door(obj)
        elif kind == "vase":
            self._break_vase(obj)
        else:
            self._enter_wardrobe(obj)

    def _toggle_door(self, d):
        if d.open:
            bodies = [self.cat, self.fox] + self.npcs
            if any(self._overlaps_tile(b, d.c, d.r) for b in bodies):
                self.events.append(("blocked", *d.center))
                return
            d.open = False
            d.scratch = 0
            self.events.append(("close", *d.center))
        else:
            d.open = True
            self.events.append(("open", *d.center))

    def _break_vase(self, v):
        v.broken = True
        cells = [(v.c + dc, v.r + dr) for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0))
                 if is_floor(v.c + dc, v.r + dr)]
        if cells:
            c = min(cells, key=lambda c: dist_to(self.cat, *cell_center(*c)))
            self.shards.append(Shards(*c))
            self.pending.append([self.elapsed + VASE_DELAY, c])
        self.events.append(("crash", *v.center))

    def _enter_wardrobe(self, w):
        cat = self.cat
        cat.hidden = True
        cat.ward = w
        cat.travel = 0.0
        cat.hide_t = WARD_MAX
        cat.x, cat.y = cell_center(*w.front)
        self.events.append(("ward_in", *w.center))

    def _exit_wardrobe(self):
        cat = self.cat
        cat.hidden = False
        cat.x, cat.y = cell_center(*cat.ward.front)
        self.events.append(("ward_out", *cat.ward.center))
        cat.ward = None
        cat.ward_cd = WARD_COOLDOWN
        cat.act_cd = ACT_COOLDOWN

    def _travel(self, dx, dy):
        """The hidden cat moves to the nearest wardrobe in the given direction."""
        cur = self.cat.ward
        cx, cy = cur.center
        best, score = None, 1e9
        for w in self.wardrobes:
            if w is cur:
                continue
            vx, vy = w.center[0] - cx, w.center[1] - cy
            l = math.hypot(vx, vy)
            cos = (vx * dx + vy * dy) / (l * math.hypot(dx, dy))
            if cos > 0.3:
                s = l * (2 - cos)
                if s < score:
                    best, score = w, s
        if best:
            self.cat.travel = WARD_TRAVEL
            self.cat.travel_to = best

    # --- fox ------------------------------------------------------------
    def _update_fox(self, dt, fi):
        fox = self.fox
        fox.dash_cd = max(0.0, fox.dash_cd - dt)
        fox.dash_t = max(0.0, fox.dash_t - dt)
        fox.summon_cd = max(0.0, fox.summon_cd - dt)
        fox.boost = max(0.0, fox.boost - dt)
        for d in self.doors.values():
            d.scratching = False
        if fox.cage > 0:                           # in the pet carrier: tap to get out
            fox.cage -= dt
            fox.moving = False
            if fi.get("act"):
                fox.cage_taps += 1
                self.events.append(("tap", fox.x, fox.y))
                if fox.cage_taps >= CARRIER_TAPS:
                    fox.cage = 0.0
            if fox.cage <= 0:
                fox.cage = 0.0
                self.events.append(("escape", fox.x, fox.y))
            return
        if fox.sleep > 0:
            fox.sleep -= dt
            fox.moving = False
            return
        if fox.stun > 0:
            fox.stun -= dt
            fox.moving = False
            return
        if fox.hold > 0 or fox.kiss > 0:
            fox.hold = max(0.0, fox.hold - dt)
            fox.kiss = max(0.0, fox.kiss - dt)
            fox.moving = False
            return
        if fox.eat > 0:
            fox.eat -= dt
            fox.moving = False
            if fox.eat <= 0:
                fox.boost = CHICKEN_BOOST
            return
        if fi.get("act") and fox.dash_cd <= 0:
            fox.dash_t = DASH_TIME
            fox.dash_cd = DASH_COOLDOWN
            self.events.append(("dash", fox.x, fox.y))
        mx, my = self._norm(fi.get("dx", 0), fi.get("dy", 0))
        speed = fox.speed
        if fox.dash_t > 0:
            speed *= DASH_MULT
        if fox.boost > 0:
            speed *= CHICKEN_MULT
        if self.on_shards(fox):
            speed *= SHARD_SLOW
        for cell in self._move(fox, mx, my, speed, dt):
            if cell in self.doors:
                self.doors[cell].scratching = True
        yol = self.npc("yolanta")
        if (fi.get("summon") and fox.summon_cd <= 0 and yol and yol.mode != "perk"
                and yol.holding <= 0 and not self.cat.hidden):
            self.events.append(("npc_gone", yol.x, yol.y))
            yol.x, yol.y = self._gran_spawn()
            yol.mode, yol.perk_t, yol.target, yol.goal = "perk", GRAN_LIFE, "cat", None
            fox.summon_cd = GRAN_COOLDOWN
            self.events.append(("summon_gran", yol.x, yol.y))

    def on_shards(self, b):
        c = cell_of(b)
        return any((s.c, s.r) == c for s in self.shards)

    # --- world ----------------------------------------------------------
    def _update_doors(self, dt):
        for d in self.doors.values():
            if d.scratching and not d.open:
                d.scratch += dt
                if d.scratch >= SCRATCH_TIME:
                    d.open = True
                    d.scratch = 0
                    self.events.append(("break", *d.center))
            else:
                d.scratch = max(0.0, d.scratch - dt * 0.5)

    def _place_beds(self):
        dist_map, _ = self._bfs(CAT_SPAWN)
        fox_map, _ = self._bfs(FOX_SPAWN)
        cands = [c for c, d in dist_map.items() if is_floor(*c) and d >= 6 and fox_map.get(c, 0) >= 6
                 and c not in SWITCHES]
        beds = []
        for _ in range(BEDS):
            far = [c for c in cands if all(abs(c[0] - b.c) + abs(c[1] - b.r) >= 10 for b in beds)] or cands
            if far:
                beds.append(Bed(*self.rng.choice(far)))
        return beds

    def _update_items(self, dt):
        cat, fox = self.cat, self.fox
        # comfy pet beds
        for b in self.beds:
            b.cool = max(0.0, b.cool - dt)
            if b.cool > 0:
                continue
            bx, by = b.center
            if not cat.hidden and cat.sleep <= 0 and cat.hold <= 0 and dist_to(cat, bx, by) < 14:
                cat.sleep, b.cool = SLEEP_TIME, BED_REST
                cat.x, cat.y = bx, by
                self.events.append(("sleep", bx, by))
            elif self.fox_free() and dist_to(fox, bx, by) < 14:
                fox.sleep, b.cool = SLEEP_TIME, BED_REST
                fox.dash_t = 0
                fox.x, fox.y = bx, by
                self.events.append(("sleep", bx, by))
        # fish
        self.fish_timer = max(0.0, self.fish_timer - dt)
        if len(self.fish) < FISH_ON_MAP and self.fish_timer <= 0:
            self._spawn_fish()
        if not cat.hidden:
            for f in list(self.fish):
                if dist(cat, f) < PICK_DIST:
                    self.fish.remove(f)
                    self.fish_got += 1
                    self.fish_timer = FISH_RESPAWN
                    self.events.append(("fish", f.x, f.y))
                    if self.fish_got >= FISH_WIN:
                        self._win("cat", "fish")
                        return
        # chicken
        if self.chicken is None:
            self.chicken_timer -= dt
            if self.chicken_timer <= 0:
                self.chicken = Item(*cell_center(*self.rng.choice(KITCHEN)))
                self.events.append(("chicken", self.chicken.x, self.chicken.y))
        elif self.fox_free() and fox.eat <= 0 and dist(fox, self.chicken) < PICK_DIST:
            self.events.append(("chomp", self.chicken.x, self.chicken.y))
            self.chicken = None
            self.chicken_timer = CHICKEN_RESPAWN
            fox.eat = CHICKEN_EAT
            fox.dash_t = 0
        # shards
        for s in list(self.shards):
            s.life -= dt
            if s.life <= 0:
                self.shards.remove(s)

    def _update_wardrobes(self, dt):
        cat, fox = self.cat, self.fox
        for w in self.wardrobes:
            w.cool = max(0.0, w.cool - dt)
            fx, fy = cell_center(*w.front)
            if (cat.hidden and self.fox_free() and fox.eat <= 0 and w.cool <= 0
                    and dist_to(fox, fx, fy) < SNIFF_DIST):
                w.sniff += dt
                if w.sniff >= SNIFF_TIME:
                    w.sniff = 0
                    w.cool = 1.5
                    if cat.ward is w and cat.travel <= 0:
                        cat.hidden = False
                        cat.x, cat.y = fx, fy
                        self._win("fox", "wardrobe")
                        return
                    self.events.append(("empty", *w.center))
            else:
                w.sniff = max(0.0, w.sniff - dt)

    def _update_npcs(self, dt):
        fox = self.fox
        for n in list(self.npcs):
            if n.kind in ("janis", "yolanta"):
                self._update_resident(n, dt)
                if self.winner:
                    return
                continue
            n.life -= dt                      # the black cat
            if n.life <= 0:
                self._remove(n)
                continue
            self._chase(n, fox, dt)
            if fox.stun <= 0 and fox.cage <= 0 and dist(n, fox) < BLACKCAT_REACH:
                fox.hearts -= 1
                fox.stun = FOX_HIT_STUN
                fox.eat = 0
                fox.dash_t = 0
                self.npcs.remove(n)
                self.events.append(("hit_fox", fox.x, fox.y))
                if fox.hearts <= 0:
                    self._win("cat", "hearts")
                    return

    # --- Janis & Yolanta, the residents -------------------------------------
    def _zone_cells(self, kind):
        rooms = LEVEL["residents"][kind]
        return [(c, r) for r in range(ROWS) for c in range(COLS)
                if MAP[r][c] == "." and room_of(c, r) in rooms]

    def _make_resident(self, kind):
        cells = self._zone_cells(kind)
        far = [c for c in cells
               if abs(c[0] - CAT_SPAWN[0]) + abs(c[1] - CAT_SPAWN[1]) >= 6
               and abs(c[0] - FOX_SPAWN[0]) + abs(c[1] - FOX_SPAWN[1]) >= 6] or cells
        n = Npc(kind, *cell_center(*self.rng.choice(far)), RES_PATROL_SPEED, 1e9)
        n.mode = "patrol"
        n.pause = self.rng.uniform(*RES_PAUSE)
        n.ignore = {"cat": 3.0, "fox": 3.0}
        return n

    def _sees(self, n, b, radius):
        """Within reach and not behind a wall or a closed door."""
        d = dist(n, b)
        if d > radius:
            return False
        steps = int(d // 8) + 1
        for i in range(1, steps):
            t = i / steps
            c, r = int((n.x + (b.x - n.x) * t) // TILE), int((n.y + (b.y - n.y) * t) // TILE)
            ch = MAP[r][c]
            if ch == "#" or (ch == "D" and not self.doors[(c, r)].open):
                return False
        return True

    def _grabbable(self, who, n):
        if n.ignore[who] > 0:
            return False
        if who == "cat":
            return not self.cat.hidden and self.cat.hold <= 0
        return self.fox_free()

    def _spawn_janis(self, blackout):
        """The lights went out: Janis heads for the nearest switch."""
        j = self.npc("janis")
        if not j or j.carrying:
            return
        dist_map, _ = self._bfs(cell_of(j))
        sw = min(SWITCHES, key=lambda c: dist_map.get(c, 999))
        j.mode, j.blackout, j.goal_cell, j.goal, j.target = "lights", blackout, sw, Item(*cell_center(*sw)), None
        self.events.append(("helper_in_janis", j.x, j.y))

    def _vase_responder(self, cell):
        """Someone heard the crash: the nearest of Janis and Yolanta who isn't busy."""
        dist_map, _ = self._bfs(cell)
        free = [n for n in self.npcs if n.kind in ("janis", "yolanta") and n.mode == "patrol" and n.holding <= 0]
        if not free:
            return False
        n = min(free, key=lambda n: dist_map.get(cell_of(n), 999))
        n.mode, n.goal_cell, n.goal, n.target = "vase", cell, Item(*cell_center(*cell)), None
        self.events.append(("helper_in_" + n.kind, n.x, n.y))
        return True

    def _update_resident(self, n, dt):
        cat, fox = self.cat, self.fox
        for k in n.ignore:
            n.ignore[k] = max(0.0, n.ignore[k] - dt)
        if n.carrying:                                  # walking Walter to the pet carrier
            fox.hold, fox.held_by = 1.0, "janis"
            n.speed = JANIS_SPEED
            self._chase(n, n.goal, dt)
            fox.x, fox.y = n.x, n.y
            if dist(n, n.goal) < 8:
                n.carrying = False
                fox.hold = 0.0
                fox.x, fox.y = n.goal.x, n.goal.y
                fox.cage, fox.cage_taps = CARRIER_TIME, 0
                n.ignore["fox"] = RES_IGNORE + CARRIER_TIME
                n.victim = n.target = None
                n.mode = "patrol"                       # and off he goes, out of the way
                n.goal_cell = self.rng.choice(self._zone_cells("janis"))
                n.goal, n.pause = Item(*cell_center(*n.goal_cell)), 0.0
                self.events.append(("carrier", fox.x, fox.y))
                bo = next((b for b in self.blackouts if b[0] <= self.elapsed < b[1]), None)
                if bo is not None:                      # it got dark meanwhile: off to the switch
                    self._spawn_janis(bo)
            return
        if n.holding > 0:
            n.holding -= dt
            n.moving = False
            if n.holding <= 0:
                n.ignore[n.victim] = RES_IGNORE
                n.victim = n.target = None
                if n.mode == "perk":
                    n.mode = "patrol"
            return
        if n.mode == "lights" and not self.dark:
            n.mode, n.goal = "patrol", None
        if n.mode == "vase" and not any((s.c, s.r) == n.goal_cell for s in self.shards):
            n.mode, n.goal = "patrol", None
        if n.mode == "perk":
            n.perk_t -= dt
            if n.perk_t <= 0:
                n.mode, n.goal, n.target = "patrol", None, None

        # whom do they go after?
        target = None
        if n.mode == "perk":
            if self._grabbable("cat", n):
                target = ("cat", cat)                 # summoned for the kitten: she knows where it is
        else:
            radii = RES_NOTICE[n.kind]
            if n.mode in ("lights", "vase"):          # busy: only grab whoever comes close
                radii = {k: JANIS_NOTICE for k in radii}
            best = None
            for who, b in (("fox", fox), ("cat", cat)):
                if not self._grabbable(who, n):
                    continue
                rad = radii[who] * (1.6 if n.target == who else 1.0)
                if self._sees(n, b, rad):
                    score = dist(n, b) / radii[who]
                    if best is None or score < best[0]:
                        best = (score, who, b)
            if best:
                n.target, n.lost = best[1], 0.0
                target = (best[1], best[2])
            elif n.target and self._grabbable(n.target, n) and n.lost < RES_LOSE:
                n.lost += dt
                target = (n.target, cat if n.target == "cat" else fox)
            else:
                n.target = None

        if target:
            who, b = target
            n.speed = GRAN_SPEED if n.mode == "perk" else RES_CHASE_SPEED[n.kind]
            self._chase(n, b, dt)
            if dist(n, b) < JANIS_REACH:
                self._grab(n, who, b)
            return

        # otherwise: their own business
        if n.mode == "perk":                          # the kitten is hiding: she waits, puzzled
            n.moving = False
            return
        if n.mode == "lights":
            n.speed = JANIS_SPEED
        elif n.mode == "vase":
            n.speed = RES_CHASE_SPEED[n.kind]
        else:
            n.speed = RES_PATROL_SPEED
            if n.goal is None:
                if n.pause > 0:
                    n.pause -= dt
                    n.moving = False
                    return
                n.goal_cell = self.rng.choice(self._zone_cells(n.kind))
                n.goal = Item(*cell_center(*n.goal_cell))
        if n.mode == "lights" and dist(n, n.goal) < 6 and self.elapsed < n.blackout[0] + DARK_MIN:
            n.moving = False                           # fumbling with the switch in the dark
            return
        self._chase(n, n.goal, dt)
        if dist(n, n.goal) < 6:
            if n.mode == "lights" and self.elapsed < n.blackout[0] + DARK_MIN:
                return                                 # waits at the switch a moment longer
            if n.mode == "lights":
                n.blackout[1] = self.elapsed           # lights back on early
                self.events.append(("lights_on", n.x, n.y))
            elif n.mode == "vase":
                self.shards = [s for s in self.shards if (s.c, s.r) != n.goal_cell]
                self.events.append(("tidy", n.x, n.y))
            n.mode, n.goal = "patrol", None
            n.pause = self.rng.uniform(*RES_PAUSE)

    def _grab(self, n, who, b):
        cat, fox = self.cat, self.fox
        n.facing = 1 if b.x > n.x else -1
        if who == "cat":
            n.holding = cat.hold = GRAN_HOLD if n.mode == "perk" else JANIS_HOLD
            cat.held_by = n.kind
            n.victim = "cat"
            self.events.append(("hold" if n.kind == "yolanta" else "grab_janis", cat.x, cat.y))
        elif n.kind == "janis" and self.rng.random() < JANIS_KISS_CHANCE:
            fox.kiss = JANIS_KISS
            fox.dash_t = 0
            n.ignore["fox"] = RES_IGNORE + JANIS_KISS
            n.target = None
            self.events.append(("kiss", fox.x, fox.y))
        else:
            n.holding = fox.hold = JANIS_HOLD
            fox.held_by = n.kind
            fox.dash_t = 0
            n.victim = "fox"
            if n.kind == "janis":
                self.janis_catches += 1
                if self.janis_catches >= CARRIER_AFTER:     # "That's it, young man. The carrier."
                    self.janis_catches = 0
                    n.holding = 0.0
                    n.carrying = True
                    n.goal_cell = LEVEL["carrier"]
                    n.goal = Item(*cell_center(*n.goal_cell))
                    self.events.append(("to_carrier", fox.x, fox.y))
            self.events.append(("grab_janis_fox" if n.kind == "janis" else "grab_yolanta", fox.x, fox.y))

    def _remove(self, n):
        self.npcs.remove(n)
        self.events.append(("npc_gone", n.x, n.y))

    def _win(self, who, reason):
        self.winner = who
        self.reason = reason
        self.events.append(("win_" + who, self.cat.x, self.cat.y))
