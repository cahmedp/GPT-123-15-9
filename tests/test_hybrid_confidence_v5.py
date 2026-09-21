
from hybrid.hybrid_confidence_v5 import HybridConfidenceEngine


class Report:
    def __init__(self, status, scenario, quality):
        self.status = status
        self.scenario = scenario
        self.quality_score = quality


class Conflict:
    def __init__(self, penalty):
        self.penalty = penalty


def run():

    engine = HybridConfidenceEngine()

    print("\n================")
    print("3 AGENTS NO CONFLICT")

    print(
        engine.calculate(
            [
                Report("VALID", "BULLISH_EXPANSION", 1),
                Report("VALID", "BULLISH_EXPANSION", .9),
                Report("VALID", "BULLISH_EXPANSION", .95),
            ],
            Conflict(0)
        )
    )

    print("\n================")
    print("WITH CONFLICT")

    print(
        engine.calculate(
            [
                Report("VALID", "BULLISH_EXPANSION", 1),
                Report("VALID", "BULLISH_EXPANSION", .9),
                Report("VALID", "BEARISH_EXPANSION", .8),
                Report("VALID", "RANGE", .7),
            ],
            Conflict(.25)
        )
    )


if __name__ == "__main__":
    run()
