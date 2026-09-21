
"""
Trader Consensus Integration Test
"""

from agents.trader_consensus import TraderConsensus
from learning.persistent_trader_memory import (
    PersistentTraderMemory
)


class MockTrader:

    def __init__(self, view):
        self.view = view



def run():

    structure = MockTrader(
        "FOLLOW_STRUCTURE"
    )

    liquidity = MockTrader(
        "CLEAR"
    )

    learning = {
        "view":"MATCH"
    }


    print("\n================")
    print("CONSENSUS")


    result = TraderConsensus().evaluate(
        structure,
        liquidity,
        learning
    )

    print(result)


    print("\n================")
    print("MEMORY")


    memory = PersistentTraderMemory(
        "test_trader_memory.json"
    )

    memory.store(
        {
            "lesson":"break retest worked",
            "result":"MATCH"
        }
    )

    print(
        memory.all()
    )


if __name__ == "__main__":
    run()
