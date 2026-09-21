from time import time

from data.pocket_connector import MarketTick


class TickAdapter:
    """
    Convert Pocket Option tick data
    into internal MarketTick model
    """

    @staticmethod
    def convert(
        tick_data: dict
    ) -> MarketTick:

        raw = tick_data["raw"]


        return MarketTick(

            timestamp=float(
                raw["timestamp"]
            ),

            price=float(
                raw["close"]
            ),

            asset=tick_data["symbol"],

            received_at=time(),

            source="pocket_option"

        )