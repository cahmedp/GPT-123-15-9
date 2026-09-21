"""
Virtual Traders Integration Test
"""


from agents.otc_structure_trader import (
    OTCStructureTrader
)

from agents.otc_liquidity_trader import (
    OTCLiquidityTrader
)

from agents.otc_learning_trader import (
    OTCLearningTrader
)


def run():

    snapshot = {
        "micro_state":"EXPANSION",
        "pattern_state":"BREAK_RETEST",
        "liquidity_state":"ACCEPTED_BREAKOUT",
        "noise_score":0.2,
    }

    print("\n================")
    print("STRUCTURE")

    structure = OTCStructureTrader().analyze(snapshot)
    print(structure)


    print("\n================")
    print("LIQUIDITY")

    liquidity = OTCLiquidityTrader().analyze(snapshot)
    print(liquidity)


    print("\n================")
    print("LEARNING")

    learner = OTCLearningTrader()

    print(
        learner.learn(
            structure.__dict__,
            {"result":"MATCH"}
        )
    )

    print(
        learner.summary()
    )


if __name__ == "__main__":
    run()
