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

BLACKOUTS = ((18.0, 32.0), (52.0, 66.0))   # lights go out twice: random moment in each window
DARK_TIME = 12.0
DARK_WARN = 1.5

JANIS_SPEED = 72         # Janis, the old gentleman: comes to switch the lights back on
JANIS_DELAY = 2.0        # he shows up a moment after the lights go out
JANIS_MIN_PATH = 10      # he comes from a door at least this far from a switch
JANIS_NOTICE = 110       # grabs anyone who comes this close
JANIS_REACH = 24
JANIS_HOLD = 2.0
JANIS_KISS_CHANCE = 0.2  # 1 in 5: kisses the fox instead of grabbing it
JANIS_KISS = 3.0         # the kissed fox is too flustered to move
JANIS_IGNORE = 4.0       # after letting someone go he leaves them alone for a while

VASE_DELAY = 2.5         # a smashed vase is loud: Janis or Yolanta come to check
VASE_DOOR_MIN = 6        # ...from the nearest door at least this far from the shards
VASE_HELPER_LIFE = 14.0

FOX_HEARTS = 3
SUMMON_FIRST = 6.0

BLACKCAT_SPEED = 140     # black cat (cat perk)
BLACKCAT_LIFE = 8.0
BLACKCAT_COOLDOWN = 18.0
BLACKCAT_REACH = 26
FOX_HIT_STUN = 1.5

GRAN_SPEED = 105         # grandma (fox perk)
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
        self.kind = kind          # "blackcat", "gran" (fox perk), "janis", "yolanta" (house residents)
        self.life = life
        self.door_t = 0.0
        self.holding = 0.0
        self.goal = None
        self.goal_cell = None
        self.mode = None
        self.blackout = None
        self.victim = None
        self.ignore = {"cat": 0.0, "fox": 0.0}


class Game:
    def __init__(self, seed=None, level=None):
        self.rng = random.Random(seed)
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
        fox.boost = 0.0

        self.npcs = []
        self.fish = []
        self.fish_got = 0
        self.fish_timer = 0.0
        for _ in range(FISH_ON_MAP):
            self._spawn_fish()
        self.chicken = None
        self.chicken_timer = CHICKEN_FIRST
        self.shards = []
        self.pending = []        # vase noise: [time, shard cell] -> someone comes to check

        self.time_left = ROUND_TIME
        self.elapsed = 0.0
        self.blackouts = []
        for a, b in BLACKOUTS:
            start = self.rng.uniform(a, b)
            self.blackouts.append([start, start + DARK_TIME])
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

    def fox_free(self):
        f = self.fox
        return f.stun <= 0 and f.hold <= 0 and f.kiss <= 0

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
                if any((s.c, s.r) == p[1] for s in self.shards):
                    self._vase_responder(p[1])

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
        if fi.get("summon") and fox.summon_cd <= 0 and not self.npc("gran") and not self.npc("yolanta") and not self.cat.hidden:
            x, y = self._gran_spawn()
            self.npcs.append(Npc("gran", x, y, GRAN_SPEED, GRAN_LIFE))
            fox.summon_cd = GRAN_COOLDOWN
            self.events.append(("summon_gran", x, y))

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

    def _update_items(self, dt):
        cat, fox = self.cat, self.fox
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
        cat, fox = self.cat, self.fox
        for n in list(self.npcs):
            n.life -= dt
            if n.kind in ("janis", "yolanta"):
                self._update_helper(n, dt)
                if self.winner:
                    return
                continue
            if n.kind == "gran":
                if n.holding > 0:
                    n.holding -= dt
                    n.moving = False
                    if n.holding <= 0:
                        self._remove(n)
                    continue
                if n.life <= 0:
                    self._remove(n)
                    continue
                if cat.hidden:
                    n.moving = False      # grandma waits, puzzled
                elif cat.hold <= 0:
                    self._chase(n, cat, dt)
                    if dist(n, cat) < GRAN_REACH:
                        n.holding = cat.hold = GRAN_HOLD
                        cat.held_by = "gran"
                        n.facing = 1 if cat.x > n.x else -1
                        self.events.append(("hold", cat.x, cat.y))
            else:
                if n.life <= 0:
                    self._remove(n)
                    continue
                self._chase(n, fox, dt)
                if fox.stun <= 0 and dist(n, fox) < BLACKCAT_REACH:
                    fox.hearts -= 1
                    fox.stun = FOX_HIT_STUN
                    fox.eat = 0
                    fox.dash_t = 0
                    self.npcs.remove(n)
                    self.events.append(("hit_fox", fox.x, fox.y))
                    if fox.hearts <= 0:
                        self._win("cat", "hearts")
                        return

    # --- Janis -----------------------------------------------------------
    def _spawn_janis(self, blackout):
        for old in [n for n in self.npcs if n.kind == "janis"]:
            self.npcs.remove(old)
        options = []
        for d in self.doors.values():
            dist_map, _ = self._bfs((d.c, d.r))
            sw = min(SWITCHES, key=lambda c: dist_map.get(c, 999))
            if dist_map.get(sw, 0) >= JANIS_MIN_PATH:
                options.append((d, sw))
        door, sw = self.rng.choice(options)
        n = self._add_helper("janis", door, sw, "lights", DARK_TIME + 3)
        n.blackout = blackout

    def _vase_responder(self, cell):
        """Someone heard the crash: Janis or Yolanta, whoever is free."""
        busy = {n.kind for n in self.npcs}
        free = []
        if "janis" not in busy:
            free.append("janis")
        if "gran" not in busy and "yolanta" not in busy:
            free.append("yolanta")
        if not free:
            return
        kind = self.rng.choice(free)
        dist_map, _ = self._bfs(cell)
        doors = sorted(self.doors.values(), key=lambda d: dist_map.get((d.c, d.r), 999))
        far = [d for d in doors if dist_map.get((d.c, d.r), 0) >= VASE_DOOR_MIN]
        self._add_helper(kind, far[0] if far else doors[-1], cell, "vase", VASE_HELPER_LIFE)

    def _add_helper(self, kind, door, goal_cell, mode, life):
        door.open = True
        n = Npc(kind, *door.center, JANIS_SPEED if kind == "janis" else GRAN_SPEED, life)
        n.goal = Item(*cell_center(*goal_cell))
        n.goal_cell = goal_cell
        n.mode = mode            # "lights" (blackout) or "vase" (came to check the noise)
        n.blackout = None
        n.victim = None
        n.ignore = {"cat": 0.0, "fox": 0.0}
        self.npcs.append(n)
        self.events.append(("helper_in_" + kind, n.x, n.y))
        return n

    def _update_helper(self, n, dt):
        """Janis and Yolanta as house residents: grab anyone in the way, then do their job."""
        cat, fox = self.cat, self.fox
        for k in n.ignore:
            n.ignore[k] = max(0.0, n.ignore[k] - dt)
        if n.holding > 0:
            n.holding -= dt
            n.moving = False
            if n.holding <= 0:
                n.ignore[n.victim] = JANIS_IGNORE
                n.victim = None
            return
        shards_here = any((s.c, s.r) == n.goal_cell for s in self.shards)
        if (n.life <= 0 or n.goal is None or (n.mode == "lights" and not self.dark)
                or (n.mode == "vase" and not shards_here)):
            self._remove(n)
            return
        # whom can they grab?
        targets = []
        if not cat.hidden and cat.hold <= 0 and n.ignore["cat"] <= 0:
            targets.append(("cat", cat))
        if self.fox_free() and n.ignore["fox"] <= 0:
            targets.append(("fox", fox))
        near = [(dist(n, b), who, b) for who, b in targets if dist(n, b) < JANIS_NOTICE]
        if near:
            d, who, b = min(near, key=lambda e: e[0])
            self._chase(n, b, dt)
            if dist(n, b) < JANIS_REACH:
                n.facing = 1 if b.x > n.x else -1
                if who == "cat":
                    n.holding = cat.hold = JANIS_HOLD
                    cat.held_by = n.kind
                    n.victim = "cat"
                    self.events.append(("grab_" + n.kind, cat.x, cat.y))
                elif n.kind == "janis" and self.rng.random() < JANIS_KISS_CHANCE:
                    fox.kiss = JANIS_KISS
                    fox.dash_t = 0
                    n.ignore["fox"] = JANIS_IGNORE + JANIS_KISS
                    self.events.append(("kiss", fox.x, fox.y))
                else:
                    n.holding = fox.hold = JANIS_HOLD
                    fox.held_by = n.kind
                    fox.dash_t = 0
                    n.victim = "fox"
                    self.events.append(("grab_" + n.kind, fox.x, fox.y))
            return
        # otherwise: off to do the job
        self._chase(n, n.goal, dt)
        if dist(n, n.goal) < 6:
            if n.mode == "lights":
                n.blackout[1] = self.elapsed           # lights back on early
                self.events.append(("lights_on", n.x, n.y))
            else:
                self.shards = [s for s in self.shards if (s.c, s.r) != n.goal_cell]
                self.events.append(("tidy", n.x, n.y))
            self._remove(n)

    def _remove(self, n):
        self.npcs.remove(n)
        self.events.append(("npc_gone", n.x, n.y))

    def _win(self, who, reason):
        self.winner = who
        self.reason = reason
        self.events.append(("win_" + who, self.cat.x, self.cat.y))
