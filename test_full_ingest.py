import asyncio

from core.orchestrator import Analyst


async def main():

    a = Analyst()

    stream = a.connector.stream_ticks()

    print("START 5M:", len(a._candles(300)))

    count = 0

    async for tick in stream:

        closed = a._ingest_live_tick(tick)

        if closed[300]:

            print("\n========== CLOSED FOUND ==========")

            print(closed[300])

            print(
                "DATA COUNT:",
                len(a._candles(300))
            )

            break

        count += 1

        if count > 500:

            print("NO CLOSE")
            break

    await a.connector.close()


asyncio.run(main())