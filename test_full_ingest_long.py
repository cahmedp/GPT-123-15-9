import asyncio
from core.orchestrator import Analyst


async def main():

    a = Analyst()

    stream = a.connector.stream_ticks()

    start = 0

    async for tick in stream:

        if start == 0:
            start = tick.timestamp

        closed = a._ingest_live_tick(tick)

        print(
            "TIME:",
            tick.timestamp,
            "5M:",
            len(a._candles(300)),
            "CLOSED:",
            len(closed[300])
        )

        if closed[300]:

            print("========== SUCCESS ==========")
            print(closed[300])
            break

        if tick.timestamp - start > 420:
            print("7 MIN PASSED WITHOUT CLOSE")
            break


    await a.connector.close()


asyncio.run(main())