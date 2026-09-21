
"""
Candle Scenario Agent with Quality Gate

Quality validation happens before scenario generation.
Bad candle windows are rejected.
"""

from dataclasses import dataclass


@dataclass
class AgentScenarioResult:
    agent_id: str
    status: str
    scenario: str
    quality_score: float
    reason: str


class CandleScenarioAgent:

    def __init__(self, agent_id, quality_validator):
        self.agent_id = agent_id
        self.quality_validator = quality_validator


    def analyze(self, candles):

        quality = self.quality_validator.validate(candles)

        if not quality.valid:
            return AgentScenarioResult(
                agent_id=self.agent_id,
                status="BLOCKED",
                scenario="NO_PATTERN",
                quality_score=quality.quality_score,
                reason="LOW_CANDLE_QUALITY"
            )


        closes = [
            c["close"]
            for c in candles
        ]

        if closes[-1] > closes[0]:
            scenario = "BULLISH_EXPANSION"

        elif closes[-1] < closes[0]:
            scenario = "BEARISH_EXPANSION"

        else:
            scenario = "RANGE"


        return AgentScenarioResult(
            agent_id=self.agent_id,
            status="ANALYZED",
            scenario=scenario,
            quality_score=quality.quality_score,
            reason="QUALITY_CONFIRMED"
        )
