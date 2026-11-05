# NitroMP WebSocket protocol — v0.1

Transport: WebSocket  
Encoding: UTF-8 JSON  
Protocol identifier: `nitromp-0.1`  
Default port: `8765`  
Scope: LAN only

## Connection

Client connects to:

- Same computer: `ws://127.0.0.1:8765`
- Another computer on the LAN: `ws://HOST_LAN_IP:8765`

The server sends `hello` immediately after connection.

## Client → server messages

### Join a room

```json
{
  "type": "join",
  "name": "Player 1",
  "room": "salon-1"
}
```

The server replies with `joined`, including the player's ID and the players already in the room.

### Update vehicle

```json
{
  "type": "vehicle_update",
  "vehicle": {
    "model": " etk800 ",
    "position": [10.0, 0.0, 3.0],
    "rotation": [0.0, 0.0, 90.0]
  }
}
```

Coordinates are placeholders for the BeamNG integration. The exact coordinate and rotation convention must be confirmed in the Lua mod.

### Ping

```json
{"type": "ping"}
```

Server replies with `pong`.

## Server → client messages

- `hello`: server greeting and protocol version
- `joined`: join accepted, your player ID, room and current players
- `player_joined`: another player entered your room
- `player_left`: another player disconnected
- `vehicle_update`: another player's latest vehicle state
- `pong`: ping response
- `error`: request rejected; includes a readable `message`

## v0.1 limits

- Maximum 16 players per room.
- One room per client connection.
- No accounts, passwords, encryption or Internet hosting.
- Vehicle updates are relayed to other clients; the server does not simulate physics.
- The first prototype uses position and rotation values only.
- Do not expose port 8765 to the public Internet in this version.
