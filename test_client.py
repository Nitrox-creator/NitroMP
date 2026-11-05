#!/usr/bin/env python3
"""Tiny terminal client for testing NitroMP v0.1 without BeamNG."""
import asyncio
import json
import sys
import websockets


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8765"
    name = sys.argv[2] if len(sys.argv) > 2 else "Test"
    room = sys.argv[3] if len(sys.argv) > 3 else "salon-1"

    async with websockets.connect(url) as ws:
        async def receiver():
            async for raw in ws:
                print("<", json.dumps(json.loads(raw), ensure_ascii=False))

        task = asyncio.create_task(receiver())
        await asyncio.sleep(0.2)
        await ws.send(json.dumps({"type": "join", "name": name, "room": room}))
        await asyncio.sleep(1)
        await ws.send(json.dumps({
            "type": "vehicle_update",
            "vehicle": {
                "model": "test-car",
                "position": [1.0, 2.0, 3.0],
                "rotation": [0.0, 0.0, 0.0]
            }
        }))
        print("Client connecté. Ctrl+C pour quitter.")
        try:
            await task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
