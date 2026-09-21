import asyncio

from data.pocket_connector import PocketConnector


async def main():

    p = PocketConnector()

    await p.connect()

    stream = p.stream_ticks()

    count = 0

    while count < 500:

        try:
            tick = await asyncio.wait_for(
                anext(stream),
                timeout=5
            )

            print(
                count,
                tick.timestamp,
                tick.price
            )

            count += 1

        except StopAsyncIteration:
            print("STREAM DIED AT:", count)
            break

        except Exception as e:
            print(
                "ERROR",
                type(e).__name__,
                e
            )
            break


    await p.close()


asyncio.run(main())