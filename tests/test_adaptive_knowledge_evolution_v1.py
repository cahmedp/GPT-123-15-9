
from knowledge.adaptive_knowledge_evolution_v1 import (
    AdaptiveKnowledgeEvolution
)


def run():

    engine = AdaptiveKnowledgeEvolution()

    print("\n================")
    print("PROMOTION")

    print(
        engine.evolve(
            "BULLISH_EXPANSION",
            0.82,
            0.78
        )
    )

    print("\n================")
    print("DECAY")

    print(
        engine.evolve(
            "BULLISH_EXPANSION",
            0.82,
            0.40
        )
    )


if __name__ == "__main__":
    run()
