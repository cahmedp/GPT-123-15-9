import asyncio

from data.pocket_connector import PocketConnector


async def main():

    connector = PocketConnector()

    await connector.connect()

    print("CONNECTOR ASSET:", connector.asset)

    stream = connector.stream_ticks()

    for i in range(20):
        tick = await anext(stream)

        print(
            i,
            "tick.asset=",
            tick.asset,
            "price=",
            tick.price
        )

    await stream.aclose()
    await connector.close()


asyncio.run(main())