import asyncio

from data.pocket_connector import PocketConnector
from data.candle_builder import CandleBuilder
from data.data_manager import DataManager
from config import CONFIG


async def main():

    connector = PocketConnector()
    data = DataManager()
    builder = CandleBuilder()

    await connector.connect()

    history = await connector.fetch_historical_candles(
        timeframe_seconds=CONFIG.BASE_TIMEFRAME_SECONDS,
        count=240,
    )

    emitted = builder.seed_base_candles(history)

    for candles in emitted.values():
        data.add_candles(candles)

    print(
        "START",
        {
            tf: len(data.candles_for("GBPUSD_otc", tf))
            for tf in builder.timeframes
        }
    )

    stream = connector.stream_ticks()

    count = 0

    while count < 100:

        tick = await asyncio.wait_for(
            anext(stream),
            timeout=5
        )

        data.add_tick(tick)

        closed = builder.add_tick(tick)

        for candles in closed.values():
            data.add_candles(candles)

        print(
            "TICK",
            tick.timestamp,
            {
                tf: len(v)
                for tf,v in closed.items()
            }
        )

        count += 1


    await connector.close()


asyncio.run(main())