import asyncio
import os

from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync


load_dotenv()


def build_ssid():

    return (
        '42["auth",'
        '{'
        f'"session":"{os.getenv("POCKET_SESSION_ID")}",'
        '"isDemo":true,'
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

    await client.client.connect()

    print("CONNECTED")


    print("RAW STREAM START")


    stream = await client.subscribe_raw()


    async for message in stream:

        print("=" * 80)

        print(type(message))

        print(message)

        break


    await client.shutdown()



asyncio.run(main())