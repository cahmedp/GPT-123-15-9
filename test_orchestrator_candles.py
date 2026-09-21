from core.orchestrator import Analyst
from data.pocket_connector import HistoricalCandle

a = Analyst()

c = HistoricalCandle(
    timestamp=1789671900.0,
    open=1.33516,
    high=1.3352,
    low=1.33501,
    close=1.33503,
    asset="GBPUSD",
    timeframe_seconds=300,
    source="test"
)

a.data.add_candle(c)

print("DATA:")
print(a.data.latest_candles())

print("\nANALYST 5M:")
print(a._candles(300))