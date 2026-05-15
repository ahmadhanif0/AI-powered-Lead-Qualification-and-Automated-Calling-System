import asyncio
import websockets
import json


async def listen():

    uri = "ws://127.0.0.1:8000/ws"

    async with websockets.connect(uri) as websocket:

        print("Connected to WebSocket")

        while True:
            message = await websocket.recv()
            print("LIVE EVENT:", json.loads(message))


asyncio.run(listen())