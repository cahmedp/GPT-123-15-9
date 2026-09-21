import asyncio

from core.orchestrator import Analyst
from config import CONFIG


async def main():

    a = Analyst()

    a.session.start()

    await a.connector.connect()

    await a._bootstrap_history()

    for tf in a.candle_builder.timeframes:
        candles = a._candles(tf)

        assets = set(
            c.asset
            for c in candles
        )

        print(
            "TIMEFRAME",
            tf,
            "COUNT",
            len(candles),
            "ASSETS",
            assets,
        )


asyncio.run(main())