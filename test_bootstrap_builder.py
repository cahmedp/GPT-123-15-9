import asyncio

from data.pocket_connector import PocketConnector
from data.candle_builder import CandleBuilder
from config import CONFIG


async def main():

    connector = PocketConnector()

    await connector.connect()

    print("ASSET =", connector.asset)

    candles = await connector.fetch_historical_candles(
        timeframe_seconds=CONFIG.BASE_TIMEFRAME_SECONDS,
        count=CONFIG.MIN_BASE_CANDLES,
    )

    print("BASE HISTORY =", len(candles))


    builder = CandleBuilder()

    emitted = builder.seed_base_candles(
        candles
    )


    print("\nRESULT:")

    for timeframe, items in emitted.items():

        print(
            timeframe,
            "seconds =",
            len(items),
            "candles"
        )


    await connector.close()


if __name__ == "__main__":
    asyncio.run(main())