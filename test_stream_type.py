import asyncio

from data.pocket_connector import PocketConnector


async def main():
    p = PocketConnector()

    await p.connect()

    stream = await p._subscribe_with_fallback(p._client)

    print("STREAM TYPE:")
    print(type(stream))

    print("HAS AITER:")
    print(hasattr(stream, "__aiter__"))

    print("DIR:")
    print(dir(stream)[:50])

    await p.close()


asyncio.run(main())