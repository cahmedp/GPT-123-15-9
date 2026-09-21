from collections import deque
from typing import List


class FeatureEngine:
    """
    Market Feature Extraction Layer

    مسؤول عن تحويل HistoricalCandles
    إلى Features قابلة للتحليل
    """


    def __init__(
        self,
        window: int = 20
    ):

        self.window = window

        self.candles = deque(
            maxlen=window
        )


    def update(
        self,
        candle
    ):

        self.candles.append(
            candle
        )


        if len(self.candles) < 3:

            return None


        return self.calculate()



    def calculate(self):

        candles = list(
            self.candles
        )


        last = candles[-1]


        close_prices = [
            c.close
            for c in candles
        ]


        ranges = [
            c.high - c.low
            for c in candles
        ]


        body = abs(
            last.close - last.open
        )


        candle_range = (
            last.high - last.low
        )


        if candle_range == 0:

            body_ratio = 0

        else:

            body_ratio = (
                body / candle_range
            )



        direction = (
            "BULLISH"
            if last.close > last.open
            else
            "BEARISH"
        )


        volatility = (
            sum(ranges)
            /
            len(ranges)
        )


        momentum = (
            close_prices[-1]
            -
            close_prices[0]
        )


        return {

            "asset": last.asset,

            "timeframe": last.timeframe_seconds,

            "close": last.close,


            "direction": direction,


            "body_ratio": round(
                body_ratio,
                4
            ),


            "volatility": round(
                volatility,
                6
            ),


            "momentum": round(
                momentum,
                6
            ),


            "samples": len(candles)

        }