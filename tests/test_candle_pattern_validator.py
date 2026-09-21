
from validation.candle_pattern_validator import (
    CandlePatternValidator
)


class Report:
    def __init__(self, pattern):
        self.pattern = pattern


def run():

    validator = CandlePatternValidator()

    reports = [
        Report("BULLISH_EXPANSION")
        for _ in range(6)
    ]


    print("\n================")
    print("VALID PATTERN")

    print(
        validator.validate(
            "BULLISH_EXPANSION",
            reports,
            200,
            150,
            0.95
        )
    )


    print("\n================")
    print("SMALL HISTORY")

    print(
        validator.validate(
            "BULLISH_EXPANSION",
            reports,
            5,
            5,
            0.95
        )
    )


if __name__ == "__main__":
    run()
