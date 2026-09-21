import asyncio

from data.pocket_connector import PocketConnector
from data.candle_builder import CandleBuilder
from config import CONFIG


async def main():

    p = PocketConnector()

    await p.connect()

    print("CONNECTED")

    history = await p.fetch_historical_candles(
        timeframe_seconds=CONFIG.BASE_TIMEFRAME_SECONDS,
        count=240,
    )

    print("HISTORY", len(history))


    builder = CandleBuilder()

    emitted = builder.seed_base_candles(history)

    print(
        "SEEDED",
        {
            k: len(v)
            for k,v in emitted.items()
        }
    )


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