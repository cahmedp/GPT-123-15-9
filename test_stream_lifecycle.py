import asyncio

from data.pocket_connector import PocketConnector


async def main():

    connector = PocketConnector()

    print("STEP 1: CONNECT")
    await connector.connect()

    print("CONNECTED:", connector.connected)
    print("ASSET:", connector.asset)

    print("\nSTEP 2: HISTORY")
    candles = await connector.fetch_historical_candles(
        timeframe_seconds=30,
        count=10,
    )

    print("HISTORY:", len(candles))

    print("\nSTEP 3: STREAM CREATE")

    stream = connector.stream_ticks()

    counter = 0

    try:
        while True:

            tick = await anext(stream)

            print(
                "TICK",
                tick.timestamp,
                tick.price,
                "CONNECTED:",
                connector.connected,
                "ERROR:",
                connector.last_error,
            )

            counter += 1

            if counter >= 300:
                break

    except StopAsyncIteration:
        print("\nSTREAM DIED !!!")

        print(
            "CONNECTED:",
            connector.connected
        )

        print(
            "ERROR:",
            connector.last_error
        )

    finally:
        await connector.close()


if __name__ == "__main__":
    asyncio.run(main())