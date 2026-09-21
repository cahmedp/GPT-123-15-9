import asyncio

from data.pocket_provider import PocketProvider
from data.tick_stream import TickStream


async def main():

    provider = PocketProvider()

    await provider.connect()

    print("CONNECTED")


    await provider.client.wait_for_assets()

    print("ASSETS READY")


    stream = TickStream(
        provider.client,
        "GBPUSD_otc"
    )


    count = 0


    async for tick in stream.stream():

        print("=" * 80)

        print(tick)


        raw = tick.get("raw", {})


        print(
            "IS CLOSED:",
            raw.get("is_closed")
        )


        count += 1


        if raw.get("is_closed"):

            print("========== CLOSED CANDLE FOUND ==========")

            break


        if count >= 100:

            print(
                "========== NO CLOSED CANDLE AFTER 100 TICKS =========="
            )

            break


    await provider.close()


if __name__ == "__main__":

    asyncio.run(main())