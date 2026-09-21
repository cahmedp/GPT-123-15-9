import asyncio
import os

from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync


load_dotenv()


async def main():

    print("=" * 60)
    print("POCKET OPTION CONNECTION TEST")
    print("=" * 60)

    ssid = os.getenv("POCKET_SESSION_ID")
    uid = os.getenv("POCKET_USER_ID")
    demo = os.getenv("POCKET_IS_DEMO")

    print("\nENV CHECK")
    print("SESSION:", bool(ssid))
    print("UID:", uid)
    print("DEMO:", demo)

    if not ssid:
        raise Exception("Missing POCKET_SESSION_ID")

    print("\nConnecting...")

    client = PocketOptionAsync(ssid)

    print("Waiting authentication...")

    await client.wait_for_connection()

    print("CONNECTED")

    print("\nLoading assets...")

    await client.wait_for_assets(timeout=60)

    print("ASSETS LOADED")

    print("\nSearching GBP assets...")

    assets = await client.get_assets()

    print("\nTOTAL ASSETS:", len(assets))

    found = []

    for asset in assets:

        name = str(asset)

        if "GBP" in name.upper():
            found.append(name)

    print("\nGBP ASSETS:")
    print("-" * 40)

    for item in found:
        print(item)

    print("-" * 40)

    print("\nDONE")


if __name__ == "__main__":
    asyncio.run(main())