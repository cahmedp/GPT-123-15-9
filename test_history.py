import asyncio
from data.pocket_connector import PocketConnector


async def main():

    p = PocketConnector()

    await p.connect()

    print("ASSET =", p.asset)

    candles = await p.fetch_historical_candles(
        timeframe_seconds=30,
        count=120,
    )

    print("COUNT =", len(candles))

    for c in candles[-5:]:
        print(
            c.timestamp,
            c.open,
            c.high,
            c.low,
            c.close
        )

    await p.close()


if __name__ == "__main__":
    asyncio.run(main())