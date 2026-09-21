import asyncio

from data.pocket_connector import PocketConnector


async def main():

    p = PocketConnector()

    await p.connect()

    print("CONNECTED")

    candles = await p.fetch_historical_candles(
        timeframe_seconds=30,
        count=10,
    )

    print("HISTORY:", len(candles))

    stream = p.stream_ticks()

    count = 0

    async for tick in stream:

        print(
            "TICK",
            tick.timestamp,
            tick.price
        )

        count += 1

        if count >= 20:
            break

    await p.close()


asyncio.run(main())