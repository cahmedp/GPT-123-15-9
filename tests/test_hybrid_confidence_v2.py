
from hybrid.hybrid_confidence_v2 import (
    HybridConfidenceEngine
)


class Report:

    def __init__(self, agent, status, scenario, quality):
        self.agent_id = agent
        self.status = status
        self.scenario = scenario
        self.quality_score = quality


def run():

    engine = HybridConfidenceEngine()


    print("\n================")
    print("STRONG HYBRID")


    reports = [
        Report(
            "A1",
            "VALID",
            "BULLISH_EXPANSION",
            1.0
        ),
        Report(
            "A2",
            "VALID",
            "BULLISH_EXPANSION",
            0.9
        ),
        Report(
            "A3",
            "VALID",
            "BULLISH_EXPANSION",
            0.95
        ),
        Report(
            "A4",
            "BLOCKED",
            "NO_PATTERN",
            0
        ),
    ]

    print(
        engine.calculate(reports)
    )


    print("\n================")
    print("NOT ENOUGH AGENTS")


    print(
        engine.calculate(
            [
                Report(
                    "A1",
                    "VALID",
                    "BULLISH_EXPANSION",
                    1.0
                )
            ]
        )
    )


if __name__ == "__main__":
    run()
