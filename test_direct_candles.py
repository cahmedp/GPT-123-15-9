import asyncio

from data.pocket_connector import PocketConnector


async def main():

    p = PocketConnector()

    await p.connect()

    print("connector asset =", p.asset)

    print("calling library directly...")

    result = await p._client.get_candles(
        "GBPUSD_otc",
        30,
        10
    )

    print(type(result))
    print(len(result))
    print(result[:1])

    await p.close()


asyncio.run(main())