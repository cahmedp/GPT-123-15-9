import os
import asyncio
from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync

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

    raw = client.client

    print("CONNECTING...")

    await raw.connect()

    print("CONNECTED:", raw.is_connected())

    print("\nSTART RAW LISTENER\n")

    async for message in raw.subscribe_raw():

        print("----------------")
        print(message)

        if "asset" in str(message).lower():
            print("ASSET MESSAGE FOUND")

        if "candle" in str(message).lower():
            print("CANDLE MESSAGE FOUND")


if __name__ == "__main__":
    asyncio.run(main())