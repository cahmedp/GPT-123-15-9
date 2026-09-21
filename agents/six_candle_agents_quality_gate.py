
from dataclasses import dataclass


@dataclass
class AgentReport:
    agent_id: str
    status: str
    scenario: str
    quality_score: float


@dataclass
class HybridResult:
    valid_agents: int
    blocked_agents: int
    dominant_pattern: str
    confidence: float


class SixCandleAgentsQualityGate:

    def __init__(self, quality_validator):
        self.quality_validator = quality_validator


    def analyze_agents(self, candles_windows):

        reports = []

        for agent_id, candles in candles_windows.items():

            quality = self.quality_validator.validate(candles)

            if not quality.valid:
                reports.append(
                    AgentReport(
                        agent_id,
                        "BLOCKED",
                        "NO_PATTERN",
                        quality.quality_score
                    )
                )
                continue

            closes = [c["close"] for c in candles]

            scenario = (
                "BULLISH_EXPANSION"
                if closes[-1] > closes[0]
                else
                "BEARISH_EXPANSION"
                if closes[-1] < closes[0]
                else
                "RANGE"
            )

            reports.append(
                AgentReport(
                    agent_id,
                    "VALID",
                    scenario,
                    quality.quality_score
                )
            )

        return reports


    def build_hybrid_pattern(self, reports):

        valid = [
            r for r in reports
            if r.status == "VALID"
        ]

        blocked = [
            r for r in reports
            if r.status == "BLOCKED"
        ]

        if not valid:
            return HybridResult(
                0,
                len(blocked),
                "NO_PATTERN",
                0.0
            )

        patterns = {}

        for r in valid:
            patterns[r.scenario] = patterns.get(r.scenario, 0) + 1

        dominant = max(
            patterns,
            key=patterns.get
        )

        confidence = round(
            patterns[dominant] / len(valid),
            3
        )

        return HybridResult(
            len(valid),
            len(blocked),
            dominant,
            confidence
        )
