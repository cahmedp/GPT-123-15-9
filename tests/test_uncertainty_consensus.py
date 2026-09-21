
from agents.uncertainty_manager import (
    UncertaintyManager
)

from agents.regime_consensus import (
    RegimeConsensus
)


def run():

    manager = UncertaintyManager()


    print("\n================")
    print("LOW CONFIDENCE")

    print(
        manager.evaluate(
            "LEARNING_TRADER",
            "ALIGN",
            0.40
        )
    )


    print("\n================")
    print("DATA FAILURE")

    print(
        manager.evaluate(
            "LIQUIDITY_TRADER",
            "ALIGN",
            0.90,
            data_health=0.50
        )
    )


    print("\n================")
    print("CONSENSUS WITH ABSTAIN")


    consensus = RegimeConsensus()

    print(
        consensus.evaluate(
            {
                "STRUCTURE_TRADER":{
                    "state":"ALIGN"
                },
                "LIQUIDITY_TRADER":{
                    "state":"BLOCK"
                },
                "LEARNING_TRADER":{
                    "state":"ABSTAIN"
                }
            },
            {
                "STRUCTURE_TRADER":0.8,
                "LIQUIDITY_TRADER":0.7
            }
        )
    )


if __name__ == "__main__":
    run()
