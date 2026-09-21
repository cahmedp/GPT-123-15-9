
from hybrid.hybrid_confidence_v4 import HybridConfidenceEngine


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
    print("NO CONFLICT")

    print(
        engine.calculate(
            [
                Report("VALID","BULLISH_EXPANSION",1),
                Report("VALID","BULLISH_EXPANSION",0.9),
                Report("VALID","BULLISH_EXPANSION",0.95),
            ],
            Conflict(0)
        )
    )

    print("\n================")
    print("WITH CONFLICT")

    print(
        engine.calculate(
            [
                Report("VALID","BULLISH_EXPANSION",1),
                Report("VALID","BULLISH_EXPANSION",0.9),
                Report("VALID","BEARISH_EXPANSION",0.8),
                Report("VALID","RANGE",0.7),
            ],
            Conflict(0.25)
        )
    )


if __name__ == "__main__":
    run()
