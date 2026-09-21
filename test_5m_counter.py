import asyncio

from data.pocket_connector import PocketConnector
from data.candle_builder import CandleBuilder
from data.data_manager import DataManager
from config import CONFIG


async def main():

    connector = PocketConnector()
    builder = CandleBuilder()
    data = DataManager()

    await connector.connect()

    history = await connector.fetch_historical_candles(
        CONFIG.BASE_TIMEFRAME_SECONDS,
        240
    )

    emitted = builder.seed_base_candles(history)

    for candles in emitted.values():
        data.add_candles(candles)

    print(
        "INITIAL 5M:",
        len(data.candles_for(
            CONFIG.PAIR,
            CONFIG.TIMEFRAME_5M_SECONDS
        ))
    )


    stream = connector.stream_ticks()

    while True:

        tick = await anext(stream)

        closed = builder.add_tick(tick)

        for candles in closed.values():
            data.add_candles(candles)


        five = data.candles_for(
            CONFIG.PAIR,
            CONFIG.TIMEFRAME_5M_SECONDS
        )

        print(
            tick.timestamp,
            "5M COUNT:",
            len(five),
            "CLOSED:",
            len(closed[CONFIG.TIMEFRAME_5M_SECONDS])
        )


asyncio.run(main())