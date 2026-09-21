
from validation.replay_evaluator import (
    RealReplayEvaluator
)


def run():

    evaluator = RealReplayEvaluator()


    print("\n================")
    print("REAL MATCH")


    print(
        evaluator.evaluate(
            "BULLISH_EXPANSION",
            [{"close":100+i} for i in range(10)],
            [{"close":111+i} for i in range(5)]
        )
    )


    print("\n================")
    print("REAL FAILURE")


    print(
        evaluator.evaluate(
            "BULLISH_EXPANSION",
            [{"close":100+i} for i in range(10)],
            [{"close":90-i} for i in range(5)]
        )
    )


    print("\n================")
    print("AMBIGUOUS")


    print(
        evaluator.evaluate(
            "BULLISH_EXPANSION",
            [],
            []
        )
    )


if __name__ == "__main__":
    run()
