import asyncio

from data.pocket_connector import PocketConnector


async def main():

    p = PocketConnector()

    await p.connect()

    for count in [50, 120, 300, 500, 1000]:

        try:
            candles = await p.fetch_historical_candles(
                timeframe_seconds=30,
                count=count,
            )

            print(
                "REQUEST:",
                count,
                "RETURN:",
                len(candles)
            )

        except Exception as e:
            print(
                "REQUEST:",
                count,
                "ERROR:",
                e
            )

    await p.close()


asyncio.run(main())