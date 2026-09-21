
from dataclasses import dataclass


@dataclass
class FrameStatus:
    frame: str
    symbol: str
    status: str
    condition: str
    candles_ready: int


@dataclass
class IndicatorStatus:
    name: str
    status: str
    strength: float
    signal: str


class MarketIntelligenceMonitor:

    def frames(self):
        return [
            FrameStatus(
                "30s",
                "MICRO",
                "ACTIVE",
                "SHORT_TERM_PRESSURE",
                10
            ),
            FrameStatus(
                "1m",
                "MAIN",
                "ACTIVE",
                "BULLISH_STRUCTURE",
                10
            ),
            FrameStatus(
                "5m",
                "CONTEXT",
                "ACTIVE",
                "MARKET_EXPANSION",
                2
            )
        ]


    def indicators(self):
        return [
            IndicatorStatus(
                "EMA_TREND",
                "ONLINE",
                0.82,
                "CONFIRM"
            ),
            IndicatorStatus(
                "RSI_MOMENTUM",
                "ONLINE",
                0.75,
                "BUY_PRESSURE"
            ),
            IndicatorStatus(
                "ATR_VOLATILITY",
                "ONLINE",
                0.60,
                "MEDIUM"
            ),
            IndicatorStatus(
                "VOLUME_FLOW",
                "ONLINE",
                0.80,
                "CONFIRM"
            )
        ]


    def health_report(self):
        return {
            "frames": self.frames(),
            "indicators": self.indicators(),
            "system": "READY"
        }
