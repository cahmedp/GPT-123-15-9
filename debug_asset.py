import asyncio
from data.pocket_connector import PocketConnector


async def main():

    p = PocketConnector()

    print("INITIAL")
    print(p._asset)
    print(p._asset_candidates)

    await p.connect()

    print("\nAFTER CONNECT")
    print("asset property =", p.asset)
    print("_asset =", p._asset)

    await p.close()


asyncio.run(main())