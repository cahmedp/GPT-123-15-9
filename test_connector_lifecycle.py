import asyncio

from data.pocket_connector import PocketConnector


async def main():

    connector = PocketConnector()

    await connector.connect()

    print("CONNECTED")

    stream = connector.stream_ticks()

    count = 0

    try:
        while True:
            tick = await anext(stream)

            print(
                count,
                tick.timestamp,
                tick.price
            )

            count += 1

            if count >= 1000:
                print("STREAM SURVIVED")
                break

    except StopAsyncIteration:
        print("STREAM DIED")

    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(main())