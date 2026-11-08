"""Blue Blood online server.

Run it:      pip install websockets
             python server.py
It listens on port 8765 (or $PORT if set, e.g. on a cloud host).
Players open the game, choose "Play online" and type this server's address.
"""
import asyncio
import http
import json
import os
import random
import string
import time

import websockets

import logic
import net
from logic import Game

TICK = 1 / 30
WINS_NEEDED = 3
rooms = {}


def blank_input():
    return {"dx": 0, "dy": 0, "act": False, "summon": False}


def new_code():
    while True:
        code = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(4))
        if code not in rooms:
            return code


class Room:
    def __init__(self, code, timer):
        self.code = code
        self.timer = timer
        self.players = [None, None]
        self.inputs = [blank_input(), blank_input()]
        self.game = None
        self.state = "waiting"          # waiting | play | over | done
        self.wins = [0, 0]
        self.cat_player = 0
        self.round = 1
        self.last = None
        self.level = random.choice(list(logic.LEVELS))

    def start_round(self):
        if self.game is None:
            self.game = Game(level=self.level, round_time=self.timer)
        else:
            self.game.new_round(self.level)
        self.inputs = [blank_input(), blank_input()]
        self.state = "play"

    def next(self):
        if self.state == "over":
            self.cat_player = 1 - self.cat_player
            self.round += 1
            self.level = random.choice([n for n in logic.LEVELS if n != self.level])
            self.start_round()
        elif self.state == "done":
            self.wins, self.round, self.cat_player, self.last = [0, 0], 1, 0, None
            self.level = random.choice(list(logic.LEVELS))
            self.start_round()

    def meta(self, idx):
        return {"state": self.state, "wins": self.wins, "round": self.round, "cat_player": self.cat_player,
                "you": idx, "last": self.last, "code": self.code, "timer": self.timer}

    async def tick(self):
        if self.state == "play":
            g = self.game
            logic.use_level(g.level)
            g.step(TICK, {"cat": self.inputs[self.cat_player], "fox": self.inputs[1 - self.cat_player]})
            for inp in self.inputs:
                inp["act"] = inp["summon"] = False
            if g.winner:
                self.last = self.cat_player if g.winner == "cat" else 1 - self.cat_player
                self.wins[self.last] += 1
                self.state = "done" if self.wins[self.last] >= WINS_NEEDED else "over"
        if self.state == "waiting":
            return
        logic.use_level(self.game.level)
        for idx, ws in enumerate(self.players):
            if ws is None:
                continue
            role = "cat" if idx == self.cat_player else "fox"
            msg = {"type": "state", "meta": self.meta(idx), "game": net.snapshot(self.game, role)}
            try:
                await ws.send(json.dumps(msg))
            except Exception:
                pass


async def handler(ws, *_):
    room, idx = None, None
    try:
        async for raw in ws:
            msg = json.loads(raw)
            kind = msg.get("type")
            if kind == "host" and room is None:
                room = Room(new_code(), msg.get("timer", 90))
                room.players[0], idx = ws, 0
                rooms[room.code] = room
                await ws.send(json.dumps({"type": "room", "code": room.code}))
                print(f"room {room.code} created")
            elif kind == "join" and room is None:
                r = rooms.get(str(msg.get("code", "")).strip().upper())
                if not r or r.players[1] is not None:
                    await ws.send(json.dumps({"type": "error", "text": "No game with this code"}))
                    continue
                room, idx = r, 1
                room.players[1] = ws
                room.start_round()
                print(f"room {room.code}: second player joined, the match starts")
            elif kind == "input" and room is not None:
                inp = room.inputs[idx]
                inp["dx"] = max(-1, min(1, int(msg.get("dx", 0))))
                inp["dy"] = max(-1, min(1, int(msg.get("dy", 0))))
                inp["act"] = inp["act"] or bool(msg.get("act"))
                inp["summon"] = inp["summon"] or bool(msg.get("summon"))
            elif kind == "next" and room is not None:
                room.next()
    except websockets.ConnectionClosed:
        pass
    finally:
        if room is not None and rooms.pop(room.code, None) is not None:
            other = room.players[1 - idx]
            if other is not None:
                try:
                    await other.send(json.dumps({"type": "left"}))
                except Exception:
                    pass
            print(f"room {room.code} closed")


async def ticker():
    while True:
        t0 = time.perf_counter()
        for room in list(rooms.values()):
            await room.tick()
        await asyncio.sleep(max(0.0, TICK - (time.perf_counter() - t0)))


def process_request(connection, request):
    """Opening the server address in a browser shows a short note instead of an error
    (handy to check it's up, and it wakes a sleeping free cloud server)."""
    if request.headers.get("Upgrade", "").lower() != "websocket":
        return connection.respond(http.HTTPStatus.OK, "Blue Blood server is running.\n")
    return None


async def main():
    port = int(os.environ.get("PORT", net.PORT))
    async with websockets.serve(handler, "0.0.0.0", port, process_request=process_request):
        print(f"Blue Blood server is running on port {port}. Press Ctrl+C to stop.")
        await ticker()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
