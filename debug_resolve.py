import asyncio

from data.pocket_connector import PocketConnector


async def main():

    p = PocketConnector()

    await p.connect()

    print("SYMBOL =", p._asset_symbol)
    print("LABEL  =", p._asset_label)
    print("PROPERTY =", p.asset)

    await p.close()


asyncio.run(main())