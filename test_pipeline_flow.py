import asyncio

from data.pocket_connector import PocketConnector
from data.candle_builder import CandleBuilder
from data.data_manager import DataManager


async def main():

    connector = PocketConnector()
    await connector.connect()

    builder = CandleBuilder()
    data = DataManager()

    stream = connector.stream_ticks()

    count = 0

    async for tick in stream:

        closed = builder.add_tick(tick)

        if closed[300]:

            print("\n========== 5M CLOSED ==========")

            candle = closed[300][0]

            print("CANDLE:")
            print(candle)

            print("\nADDING TO DATA MANAGER")

            data.add_candles(closed[300])

            print(
                "DATA COUNT:",
                len(
                    data.candles_for(
                        candle.asset,
                        300
                    )
                )
            )

            break


        count += 1

        if count > 500:
            print("NO 5M CLOSE")
            break


    await connector.close()


asyncio.run(main())