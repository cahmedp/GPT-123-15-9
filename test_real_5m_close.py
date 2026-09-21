import asyncio

from data.pocket_connector import PocketConnector
from data.candle_builder import CandleBuilder


async def main():

    p = PocketConnector()
    await p.connect()

    builder = CandleBuilder()

    stream = p.stream_ticks()

    count = 0

    async for tick in stream:

        closed = builder.add_tick(tick)

        if any(closed.values()):

            print("======== CLOSED ========")

            for tf, candles in closed.items():
                if candles:
                    print(
                        "TIMEFRAME:",
                        tf,
                        candles
                    )

        count += 1

        if count > 1000:
            break


    await p.close()


asyncio.run(main())