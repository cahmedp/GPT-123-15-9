import asyncio
import websockets


WS_URL = "wss://api-eu.po.market/socket.io/?EIO=4&transport=websocket"


async def main():

    async with websockets.connect(
        WS_URL,
        ping_interval=None,
        max_size=None
    ) as ws:

        print("CONNECTED")

        while True:

            msg = await ws.recv()

            print("\nSERVER:")
            print(msg[:500])

            if msg.startswith("0"):
                await ws.send("40")
                print("SENT SOCKET OPEN")

            elif msg.startswith("40"):
                print("SOCKET READY - WAITING")


asyncio.run(main())