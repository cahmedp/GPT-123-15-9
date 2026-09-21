
"""
Trader Knowledge Adapter Test
"""

from learning.trader_knowledge_adapter import (
    TraderKnowledgeAdapter
)


def run():

    adapter = TraderKnowledgeAdapter()


    knowledge = [

        {
            "name":"break_retest",
            "state":"ACTIVE_KNOWLEDGE",
            "confidence":0.82
        },

        {
            "name":"noise_pattern",
            "state":"REJECTED_KNOWLEDGE",
            "confidence":0.80
        },

        {
            "name":"new_pattern",
            "state":"PENDING_KNOWLEDGE",
            "confidence":0.70
        }

    ]


    print("\n================")
    print("STRUCTURE TRADER")


    print(
        adapter.provide_to_trader(
            "STRUCTURE_TRADER",
            knowledge
        )
    )


    print("\n================")
    print("LIQUIDITY TRADER")


    print(
        adapter.provide_to_trader(
            "LIQUIDITY_TRADER",
            knowledge
        )
    )


if __name__ == "__main__":
    run()
