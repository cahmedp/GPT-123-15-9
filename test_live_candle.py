import asyncio
import os
import time

from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync

from data.tick_stream import TickStream
from data.candle_builder import CandleBuilder
from data.pocket_connector import MarketTick


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

    print("=" * 60)
    print("LIVE CANDLE BUILDER TEST")
    print("=" * 60)

    client = PocketOptionAsync(
        build_ssid()
    )

    print("\nConnecting...")

    await client.client.connect()

    print(
        "Connected:",
        client.is_connected()
    )

    print("\nLoading assets...")

    await client.wait_for_assets(
        timeout=60
    )

    print(
        "Assets loaded"
    )

    tick_stream = TickStream(
        client,
        "GBPUSD_otc"
    )

    candle_builder = CandleBuilder(
        timeframes=(
            30,
            60,
            300,
        )
    )

    print("\nStarting live candles...\n")

    counter = 0

    async for tick_data in tick_stream.stream():

        counter += 1

        raw = tick_data["raw"]

        market_tick = MarketTick(
            timestamp=float(
                raw.get("time")
                or raw.get("timestamp")
                or time.time()
            ),
            price=float(
                raw.get("close")
                or raw.get("price")
            ),
            asset="GBPUSD_otc",
            received_at=time.time(),
        )

        candles = candle_builder.add_tick(
            market_tick
        )

        for timeframe, closed in candles.items():

            for candle in closed:

                print("\n====================")
                print(
                    "TIMEFRAME:",
                    timeframe
                )
                print(candle)

        if counter >= 200:
            break


if __name__ == "__main__":
    asyncio.run(main())
