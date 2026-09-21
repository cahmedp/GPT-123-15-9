from typing import AsyncIterator


class TickStream:

    def __init__(
        self,
        client,
        symbol: str
    ):

        self.client = client
        self.symbol = symbol


    async def stream(
        self
    ) -> AsyncIterator[dict]:

        print(
            f"[TICK] Subscribe {self.symbol}"
        )


        subscription = await self.client.subscribe_symbol(
            self.symbol
        )


        print(
            "[TICK] Started"
        )


        async for tick in subscription:

            yield {

                "symbol": self.symbol,

                "raw": tick

            }