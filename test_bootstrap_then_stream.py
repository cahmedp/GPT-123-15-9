import asyncio

from core.orchestrator import Analyst


async def main():

    a = Analyst()

    a.session.start()
    a.dashboard.start()

    try:
        await a.connector.connect()

        print("CONNECTED")

        result = await a._bootstrap_history()

        print("BOOTSTRAP:", result)

        stream = a.connector.stream_ticks()

        print("STREAM CREATED AFTER BOOTSTRAP")

        for i in range(100):

            tick = await anext(stream)

            print(
                i,
                tick.timestamp,
                tick.price
            )

        print("SUCCESS")

    finally:
        await a.connector.close()
        a.dashboard.stop()
        a.session.close()


asyncio.run(main())