#!/usr/bin/env python3
"""
NitroMP Local Server v0.1
A small LAN-only WebSocket relay for BeamNG multiplayer experiments.

Run:
    python -m pip install -r requirements.txt
    python server.py
"""

import asyncio
import json
import logging
import socket
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

import websockets
from websockets.exceptions import ConnectionClosed

HOST = "0.0.0.0"  # Listen on all network interfaces (LAN)
PORT = 8765
MAX_MESSAGE_SIZE = 16 * 1024
MAX_PLAYERS_PER_ROOM = 16
MAX_NAME_LENGTH = 24
MAX_ROOM_LENGTH = 20
MAX_POSITION_ABS = 1_000_000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("NitroMP")


@dataclass
class Player:
    player_id: str
    websocket: object
    name: str
    room_id: Optional[str] = None
    vehicle: dict = field(default_factory=dict)


rooms: Dict[str, Dict[str, Player]] = {}
players: Dict[str, Player] = {}
lock = asyncio.Lock()


def lan_ip() -> str:
    """Best-effort LAN IP discovery; does not send application data."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def clean_text(value, fallback: str, limit: int) -> str:
    if not isinstance(value, str):
        return fallback
    value = "".join(ch for ch in value.strip() if ch.isprintable())
    return (value[:limit] or fallback)


def valid_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def clean_vehicle(data) -> dict:
    """Accept only a small, predictable position/rotation payload."""
    if not isinstance(data, dict):
        raise ValueError("vehicle doit être un objet JSON")

    position = data.get("position")
    rotation = data.get("rotation", [0, 0, 0])

    if not isinstance(position, list) or len(position) != 3:
        raise ValueError("position doit contenir [x, y, z]")
    if not isinstance(rotation, list) or len(rotation) != 3:
        raise ValueError("rotation doit contenir [x, y, z]")

    for value in position + rotation:
        if not valid_number(value) or abs(value) > MAX_POSITION_ABS:
            raise ValueError("coordonnée invalide")

    model = clean_text(data.get("model", "unknown"), "unknown", 40)
    return {
        "model": model,
        "position": [float(v) for v in position],
        "rotation": [float(v) for v in rotation],
    }


async def send_json(websocket, payload: dict):
    await websocket.send(json.dumps(payload, separators=(",", ":")))


async def broadcast(room_id: str, payload: dict, exclude: Optional[str] = None):
    room = rooms.get(room_id, {})
    recipients = [
        player.websocket
        for pid, player in room.items()
        if pid != exclude
    ]
    if recipients:
        results = await asyncio.gather(
            *(send_json(ws, payload) for ws in recipients),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                log.debug("Échec d'envoi à un client: %s", result)


async def remove_player(player_id: str):
    async with lock:
        player = players.pop(player_id, None)
        if not player:
            return
        room_id = player.room_id
        if room_id and room_id in rooms:
            rooms[room_id].pop(player_id, None)
            if not rooms[room_id]:
                rooms.pop(room_id, None)
    if room_id:
        await broadcast(room_id, {
            "type": "player_left",
            "player_id": player_id,
        })
    log.info("Joueur déconnecté: %s (%s)", player.name, player_id[:8])


async def handle_message(player: Player, message: dict):
    msg_type = message.get("type")

    if msg_type == "join":
        room_id = clean_text(message.get("room"), "salon-1", MAX_ROOM_LENGTH)
        name = clean_text(message.get("name"), "Joueur", MAX_NAME_LENGTH)

        async with lock:
            if player.room_id:
                raise ValueError("tu es déjà dans un salon")
            room = rooms.setdefault(room_id, {})
            if len(room) >= MAX_PLAYERS_PER_ROOM:
                raise ValueError("salon complet")
            player.name = name
            player.room_id = room_id
            room[player.player_id] = player
            existing = [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "vehicle": p.vehicle,
                }
                for p in room.values()
                if p.player_id != player.player_id
            ]

        await send_json(player.websocket, {
            "type": "joined",
            "player_id": player.player_id,
            "room": room_id,
            "players": existing,
            "protocol": "nitromp-0.1",
        })
        await broadcast(room_id, {
            "type": "player_joined",
            "player_id": player.player_id,
            "name": player.name,
        }, exclude=player.player_id)
        log.info("%s a rejoint le salon %s", player.name, room_id)
        return

    if msg_type == "vehicle_update":
        if not player.room_id:
            raise ValueError("rejoins un salon avant d'envoyer ta position")
        vehicle = clean_vehicle(message.get("vehicle"))
        player.vehicle = vehicle
        await broadcast(player.room_id, {
            "type": "vehicle_update",
            "player_id": player.player_id,
            "name": player.name,
            "vehicle": vehicle,
        }, exclude=player.player_id)
        return

    if msg_type == "ping":
        await send_json(player.websocket, {"type": "pong"})
        return

    raise ValueError("type de message inconnu")


async def client_handler(websocket, path=None):
    player_id = uuid.uuid4().hex[:12]
    player = Player(player_id=player_id, websocket=websocket, name="Joueur")

    async with lock:
        players[player_id] = player

    log.info("Connexion entrante: %s", websocket.remote_address)

    try:
        await send_json(websocket, {
            "type": "hello",
            "server": "NitroMP Local Server",
            "version": "0.1.0",
            "protocol": "nitromp-0.1",
            "player_id": player_id,
        })

        async for raw_message in websocket:
            try:
                message = json.loads(raw_message)
                if not isinstance(message, dict):
                    raise ValueError("chaque message doit être un objet JSON")
                await handle_message(player, message)
            except (json.JSONDecodeError, ValueError) as exc:
                await send_json(websocket, {
                    "type": "error",
                    "message": str(exc),
                })
            except Exception:
                log.exception("Erreur pendant le traitement d'un message")
                await send_json(websocket, {
                    "type": "error",
                    "message": "erreur interne du serveur",
                })
    except ConnectionClosed:
        pass
    finally:
        await remove_player(player_id)


async def main():
    ip = lan_ip()
    print()
    print("======================================")
    print("       NitroMP Local Server v0.1")
    print("======================================")
    print(f"Local : ws://127.0.0.1:{PORT}")
    print(f"LAN   : ws://{ip}:{PORT}")
    print("Protocole : nitromp-0.1")
    print("Arrêt : Ctrl+C")
    print()
    print("Important : serveur LAN uniquement.")
    print("N'ouvrez pas ce port sur Internet dans cette version.")
    print()

    async with websockets.serve(
        client_handler,
        HOST,
        PORT,
        max_size=MAX_MESSAGE_SIZE,
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nNitroMP arrêté.")
