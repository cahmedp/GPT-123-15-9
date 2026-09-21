
from core.knowledge_orchestrator_v1 import (
    KnowledgeOrchestrator
)


class Hybrid:
    confidence = 0.82


class Validation:
    state = "VALIDATED_HYBRID"
    blockers = []


def run():

    engine = KnowledgeOrchestrator()


    print("\n================")
    print("FULL PIPELINE")


    print(
        engine.run(
            "BULLISH_EXPANSION",
            Hybrid(),
            Validation()
        )
    )


    print("\n================")
    print("BLOCK PIPELINE")


    bad = Validation()
    bad.state = "PENDING_HYBRID"
    bad.blockers = [
        "LOW_CONFIDENCE"
    ]


    print(
        engine.run(
            "BULLISH_EXPANSION",
            Hybrid(),
            bad
        )
    )


if __name__ == "__main__":
    run()
