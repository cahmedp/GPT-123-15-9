import os
import asyncio

from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync


load_dotenv()


def build_ssid():

    session = os.getenv("POCKET_SESSION_ID")
    uid = os.getenv("POCKET_USER_ID")

    if not session or not uid:
        raise Exception(
            "Missing Pocket credentials"
        )

    return (
        '42["auth",'
        '{'
        f'"session":"{session}",'
        '"isDemo":1,'
        f'"uid":{uid},'
        '"platform":2,'
        '"isFastHistory":true,'
        '"isOptimized":true'
        '}'
        ']'
    )


async def main():

    print("=" * 60)
    print("POCKET RAW STREAM V2 TEST")
    print("=" * 60)

    ssid = build_ssid()

    client = PocketOptionAsync(ssid)

    raw = client.client

    print("\nConnecting...")

    await raw.connect()

    print(
        "CONNECTED:",
        raw.is_connected()
    )

    print("\nSubscribing RAW...")

    stream = await raw.subscribe_raw()

    print(
        "RAW STREAM STARTED"
    )


    async for message in stream:

        print("\n----------------------")
        print(type(message))
        print(message)


if __name__ == "__main__":
    asyncio.run(main())