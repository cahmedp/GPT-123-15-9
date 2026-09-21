import asyncio

from data.pocket_connector import PocketConnector


async def main():

    p = PocketConnector()

    await p.connect()

    stream = p.stream_ticks()

    count = 0

    async for tick in stream:

        print(
            "TIME:",
            tick.timestamp,
            "PRICE:",
            tick.price
        )

        count += 1

        if count >= 20:
            break

    await p.close()


asyncio.run(main())