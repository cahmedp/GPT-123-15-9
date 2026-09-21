
"""
Trader Knowledge Router Test
"""

from learning.trader_knowledge_router import (
    TraderKnowledgeRouter
)


def run():

    router = TraderKnowledgeRouter()


    knowledge = [

        {
            "name":"break_retest",
            "state":"ACTIVE_KNOWLEDGE",
            "target":"STRUCTURE_TRADER",
            "confidence":0.82
        },

        {
            "name":"liquidity_sweep",
            "state":"ACTIVE_KNOWLEDGE",
            "target":"LIQUIDITY_TRADER",
            "confidence":0.78
        },

        {
            "name":"bad_pattern",
            "state":"REJECTED_KNOWLEDGE",
            "target":"STRUCTURE_TRADER"
        },

        {
            "name":"confidence_lesson",
            "state":"ACTIVE_KNOWLEDGE",
            "target":"LEARNING_TRADER",
            "confidence":0.75
        }
    ]


    print("\n================")
    print("STRUCTURE")

    print(
        router.get_for_trader(
            "STRUCTURE_TRADER",
            knowledge
        )
    )


    print("\n================")
    print("LIQUIDITY")

    print(
        router.get_for_trader(
            "LIQUIDITY_TRADER",
            knowledge
        )
    )


    print("\n================")
    print("LEARNING")

    print(
        router.get_for_trader(
            "LEARNING_TRADER",
            knowledge
        )
    )


if __name__ == "__main__":
    run()
