
from validation.pattern_walk_forward import (
    PatternWalkForwardValidator
)


def run():

    validator = PatternWalkForwardValidator()


    print("\n================")
    print("FORWARD VALIDATED")


    print(
        validator.validate(
            "BULLISH_EXPANSION",
            ["DISCOVERED"] * 200,
            ["MATCH"] * 70 +
            ["FAILURE"] * 30
        )
    )


    print("\n================")
    print("FAILED FORWARD")


    print(
        validator.validate(
            "BULLISH_EXPANSION",
            ["DISCOVERED"] * 200,
            ["MATCH"] * 20 +
            ["FAILURE"] * 40
        )
    )


if __name__ == "__main__":
    run()
