import asyncio
import os

from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync

from data.tick_stream import TickStream
from data.tick_adapter import TickAdapter
from data.candle_builder import CandleBuilder


load_dotenv()


def build_ssid():

    return (
        '42["auth",'
        '{'
        f'"session":"{os.getenv("POCKET_SESSION_ID")}",'
        '"isDemo":1,'
        f'"uid":{os.getenv("POCKET_USER_ID")},'
        '"platform":2,'
        '"isFastHistory":true,'
        '"isOptimized":true'
        '}'
        ']'
    )


async def main():

    client = PocketOptionAsync(
        build_ssid()
    )

    print("Connecting...")

    await client.client.connect()

    await client.wait_for_assets(
        timeout=60
    )

    print("READY")


    ticks = TickStream(
        client,
        "GBPUSD_otc"
    )


    candles = CandleBuilder(
        timeframes=(
            30,
            60
        )
    )


    async for raw_tick in ticks.stream():

        market_tick = TickAdapter.convert(
            raw_tick
        )


        result = candles.add_tick(
            market_tick
        )


        for tf, closed in result.items():

            for candle in closed:

                print("\n================")
                print("TIMEFRAME:", tf)
                print(candle)


if __name__ == "__main__":
    asyncio.run(main())