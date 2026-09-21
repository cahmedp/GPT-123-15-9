from intelligence.feature_engine import FeatureEngine
from data.pocket_connector import HistoricalCandle


engine = FeatureEngine(
    window=5
)


candles = [

    HistoricalCandle(
        timestamp=1,
        open=1.1000,
        high=1.1010,
        low=1.0990,
        close=1.1008,
        asset="GBPUSD_otc",
        timeframe_seconds=30
    ),

    HistoricalCandle(
        timestamp=2,
        open=1.1008,
        high=1.1020,
        low=1.1000,
        close=1.1015,
        asset="GBPUSD_otc",
        timeframe_seconds=30
    ),

    HistoricalCandle(
        timestamp=3,
        open=1.1015,
        high=1.1030,
        low=1.1010,
        close=1.1025,
        asset="GBPUSD_otc",
        timeframe_seconds=30
    )

]


for candle in candles:

    result = engine.update(
        candle
    )

    if result:

        print(result)