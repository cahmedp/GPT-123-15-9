
from hybrid.hybrid_confidence_v3 import (
    HybridConfidenceEngine
)


class Report:

    def __init__(self, status, scenario, quality):
        self.status = status
        self.scenario = scenario
        self.quality_score = quality


def run():

    engine = HybridConfidenceEngine()


    print("\n================")
    print("3 AGENTS VALID")


    print(
        engine.calculate(
            [
                Report("VALID", "BULLISH_EXPANSION", 1.0),
                Report("VALID", "BULLISH_EXPANSION", 0.9),
                Report("VALID", "BULLISH_EXPANSION", 0.95),
                Report("BLOCKED", "NO_PATTERN", 0),
            ]
        )
    )


    print("\n================")
    print("1 AGENT ONLY")


    print(
        engine.calculate(
            [
                Report("VALID", "BULLISH_EXPANSION", 1.0)
            ]
        )
    )


if __name__ == "__main__":
    run()
