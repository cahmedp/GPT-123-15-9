import os
import asyncio
from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync


load_dotenv()


def build_ssid():

    session = os.getenv("POCKET_SESSION_ID")
    uid = os.getenv("POCKET_USER_ID")

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
    print("POCKET OPTION ASSET TEST")
    print("=" * 60)

    client = PocketOptionAsync(
        build_ssid()
    )

    await client.wait_for_assets(
        timeout=30
    )

    print("\nCONNECTED:")
    print(
        client.is_connected()
    )

    print("\nACTIVE ASSETS:")

    assets = client.active_assets

    print(type(assets))
    print(len(assets))

    print("\nFIRST 50:")

    for item in list(assets)[:50]:
        print(item)


if __name__ == "__main__":
    asyncio.run(main())