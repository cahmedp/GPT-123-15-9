import asyncio

from core.orchestrator import Analyst


async def main():

    a = Analyst()

    a.session.start()
    a.dashboard.start()

    try:
        await a.connector.connect()

        print("CONNECTED")

        await a._bootstrap_history()

        stream = a.connector.stream_ticks()

        print("STREAM CREATED")

        for i in range(100):
            tick = await anext(stream)

            print(
                i,
                tick.timestamp,
                tick.price,
            )

        print("STREAM OK")

    finally:
        await a.connector.close()
        a.dashboard.stop()
        a.session.close()


asyncio.run(main())