
from agents.regime_consensus import RegimeConsensus


def run():

    engine = RegimeConsensus()

    weights = {
        "STRUCTURE_TRADER":{
            "EXPANSION":0.86
        },
        "LIQUIDITY_TRADER":{
            "EXPANSION":0.70
        },
        "LEARNING_TRADER":{
            "EXPANSION":0.60
        }
    }


    print("\n================")
    print("ALIGNED")

    print(
        engine.evaluate(
            {
                "STRUCTURE_TRADER":"FOLLOW_STRUCTURE",
                "LIQUIDITY_TRADER":"CLEAR",
                "LEARNING_TRADER":"MATCH"
            },
            weights,
            "EXPANSION"
        )
    )


    print("\n================")
    print("REAL CONFLICT")

    print(
        engine.evaluate(
            {
                "STRUCTURE_TRADER":"FOLLOW_STRUCTURE",
                "LIQUIDITY_TRADER":"WAIT",
                "LEARNING_TRADER":"MATCH"
            },
            weights,
            "EXPANSION"
        )
    )


if __name__ == "__main__":
    run()
