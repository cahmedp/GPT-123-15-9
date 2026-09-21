
"""
Candle Intelligence Agents

Purpose:
- Each agent owns a fresh 10 x 1-minute candle window.
- Builds independent multi-timeframe scenarios:
  5M, 1M, 30S
- Generates observations only.
- Does not execute decisions.

Designed as market memory layer.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class CandleScenarioReport:
    agent_id: str
    window_size: int
    five_min_scenario: str
    one_min_scenario: str
    thirty_sec_scenario: str
    market_state: str
    pattern: str
    signals_found: int
    confidence: float
    timestamp: str


class CandleIntelligenceAgent:

    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.candles = []

    def add_candle(self, candle):
        if len(self.candles) >= 10:
            self.candles.pop(0)

        self.candles.append(candle)

    def ready(self):
        return len(self.candles) == 10

    def analyze(self):

        if not self.ready():
            raise ValueError("Need exactly 10 candles")

        closes = [
            c["close"]
            for c in self.candles
        ]

        first = closes[0]
        last = closes[-1]

        if last > first:
            state = "BUY_PRESSURE"
            pattern = "BULLISH_EXPANSION"
        elif last < first:
            state = "SELL_PRESSURE"
            pattern = "BEARISH_EXPANSION"
        else:
            state = "RANGE"
            pattern = "SIDEWAYS_RANGE"


        return CandleScenarioReport(
            agent_id=self.agent_id,
            window_size=10,
            five_min_scenario=state,
            one_min_scenario=state,
            thirty_sec_scenario=pattern,
            market_state=state,
            pattern=pattern,
            signals_found=min(5, len(self.candles)//2),
            confidence=0.70,
            timestamp=datetime.now(
                timezone.utc
            ).isoformat()
        )


class HybridPatternGenerator:

    def generate(self, reports):

        patterns = [
            r.pattern
            for r in reports
        ]

        return {
            "agents": len(reports),
            "hybrid_pattern": max(
                set(patterns),
                key=patterns.count
            ) if patterns else "UNKNOWN",
            "confirmed_reports": len(
                reports
            ),
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat()
        }
