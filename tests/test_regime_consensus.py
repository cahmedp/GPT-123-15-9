
"""
Regime Consensus Test
"""

from agents.regime_consensus import (
    RegimeConsensus
)


def run():

    engine = RegimeConsensus()


    weights = {

        "STRUCTURE_TRADER": {
            "EXPANSION": 0.86,
            "RANGE": 0.40
        },

        "LIQUIDITY_TRADER": {
            "EXPANSION": 0.70,
            "RANGE": 0.82
        },

        "LEARNING_TRADER": {
            "EXPANSION": 0.60,
            "RANGE": 0.60
        }
    }


    print("\n================")
    print("EXPANSION")


    print(
        engine.evaluate(
            {
                "STRUCTURE_TRADER":
                    "FOLLOW_STRUCTURE",

                "LIQUIDITY_TRADER":
                    "CLEAR",

                "LEARNING_TRADER":
                    "MATCH"
            },
            weights,
            "EXPANSION"
        )
    )


    print("\n================")
    print("RANGE CONFLICT")


    print(
        engine.evaluate(
            {
                "STRUCTURE_TRADER":
                    "FOLLOW_STRUCTURE",

                "LIQUIDITY_TRADER":
                    "WAIT",

                "LEARNING_TRADER":
                    "MATCH"
            },
            weights,
            "RANGE"
        )
    )


if __name__ == "__main__":
    run()
