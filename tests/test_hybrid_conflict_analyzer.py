
from hybrid.hybrid_conflict_analyzer import HybridConflictAnalyzer


class Report:
    def __init__(self, status, scenario):
        self.status = status
        self.scenario = scenario


def run():

    analyzer = HybridConflictAnalyzer()

    print("\n================")
    print("NO CONFLICT")

    print(
        analyzer.analyze(
            [
                Report("VALID", "BULLISH_EXPANSION"),
                Report("VALID", "BULLISH_EXPANSION"),
                Report("VALID", "BULLISH_EXPANSION"),
            ]
        )
    )

    print("\n================")
    print("REAL CONFLICT")

    print(
        analyzer.analyze(
            [
                Report("VALID", "BULLISH_EXPANSION"),
                Report("VALID", "BULLISH_EXPANSION"),
                Report("VALID", "BEARISH_EXPANSION"),
                Report("VALID", "RANGE"),
            ]
        )
    )


if __name__ == "__main__":
    run()
