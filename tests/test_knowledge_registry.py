
"""
Knowledge Registry Test
"""

from learning.knowledge_registry import (
    KnowledgeRegistry
)


def run():

    registry = KnowledgeRegistry(
        min_samples=50
    )


    print("\n================")
    print("PENDING")


    print(
        registry.evaluate(
            "break_retest",
            samples=20,
            success_rate=0.90
        )
    )


    print("\n================")
    print("ACTIVE")


    print(
        registry.evaluate(
            "expansion_pattern",
            samples=200,
            success_rate=0.82,
            calibrated=True,
            counterfactual_checked=True
        )
    )


    print("\n================")
    print("REJECTED")


    print(
        registry.evaluate(
            "noise_pattern",
            samples=100,
            success_rate=0.80,
            calibrated=False
        )
    )


if __name__ == "__main__":
    run()
