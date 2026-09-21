import asyncio
import os

from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync

from data.tick_stream import TickStream


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
    print("POCKET TICK STREAM TEST")
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


    print("\nStarting tick stream...")


    stream = TickStream(
        client,
        "GBPUSD_otc"
    )


    async for tick in stream.stream():

        print(tick)



if __name__ == "__main__":

    asyncio.run(main())