class MarketStateEngine:
    """
    Convert market features
    into readable market state
    """


    def analyze(
        self,
        features: dict
    ) -> dict:


        if not features:

            return None



        # Trend

        if features["momentum"] > 0:

            trend = "UP"

        elif features["momentum"] < 0:

            trend = "DOWN"

        else:

            trend = "FLAT"



        # Momentum

        if abs(features["momentum"]) > 0.001:

            momentum = "STRONG"

        elif abs(features["momentum"]) > 0:

            momentum = "WEAK"

        else:

            momentum = "NONE"



        # Volatility

        volatility_value = features["volatility"]


        if volatility_value > 0.003:

            volatility = "HIGH"

        elif volatility_value > 0.001:

            volatility = "NORMAL"

        else:

            volatility = "LOW"



        # Candle strength

        body = features["body_ratio"]


        if body > 0.7:

            candle_power = "STRONG"

        elif body > 0.3:

            candle_power = "MEDIUM"

        else:

            candle_power = "WEAK"



        # Market condition

        if (
            trend != "FLAT"
            and momentum != "NONE"
        ):

            mode = "TRENDING"

        else:

            mode = "RANGING"



        return {

            "asset": features["asset"],

            "timeframe": features["timeframe"],

            "trend": trend,

            "momentum": momentum,

            "volatility": volatility,

            "candle_power": candle_power,

            "market_mode": mode

        }