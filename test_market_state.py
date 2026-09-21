from intelligence.market_state import MarketStateEngine


engine = MarketStateEngine()


features = {

    "asset": "GBPUSD_otc",

    "timeframe": 30,

    "direction": "BULLISH",

    "body_ratio": 0.5,

    "volatility": 0.002,

    "momentum": 0.0017,

    "close": 1.1025,

    "samples": 3

}


state = engine.analyze(
    features
)


print(state)