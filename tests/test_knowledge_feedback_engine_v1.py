
from knowledge.knowledge_feedback_engine_v1 import (
    KnowledgeFeedbackEngine
)

from knowledge.knowledge_memory_v3 import (
    KnowledgeMemoryManager
)


def run():

    manager = KnowledgeMemoryManager()

    memory = manager.create(
        "BULLISH_EXPANSION",
        "EXPANSION",
        "30s-1m-5m",
        0.82
    )

    engine = KnowledgeFeedbackEngine()


    print("\n================")
    print("MATCH")

    print(
        engine.evaluate(
            memory,
            "CALL",
            "CALL",
            1
        )
    )


    print("\n================")
    print("MISMATCH")

    print(
        engine.evaluate(
            memory,
            "CALL",
            "PUT",
            -1
        )
    )


if __name__ == "__main__":
    run()
