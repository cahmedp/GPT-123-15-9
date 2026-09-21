
from validation.pattern_statistics import (
    PatternStatisticsEngine
)


def run():

    engine = PatternStatisticsEngine()


    print("\n================")
    print("REAL PATTERN STATS")


    print(
        engine.calculate(
            "BULLISH_EXPANSION",
            [
                "MATCH"
            ] * 70 +
            [
                "FAILURE"
            ] * 20 +
            [
                "AMBIGUOUS"
            ] * 10,
            {
                "EXPANSION":0.78,
                "RANGE":0.42
            }
        )
    )


    print("\n================")
    print("SMALL SAMPLE")


    print(
        engine.calculate(
            "BULLISH_EXPANSION",
            [
                "MATCH"
            ] * 5
        )
    )


if __name__ == "__main__":
    run()
