
from knowledge.knowledge_memory_v3 import (
    KnowledgeMemoryManager
)


def run():

    manager = KnowledgeMemoryManager()


    print("\n================")
    print("CREATE MEMORY")

    item = manager.create(
        "BULLISH_EXPANSION",
        "EXPANSION",
        "30s-1m-5m",
        0.82
    )

    print(item)


    print("\n================")
    print("ADD EVIDENCE")

    print(
        manager.add_evidence(
            item,
            "replay",
            {
                "samples":100,
                "success_rate":0.78
            }
        )
    )


    print("\n================")
    print("VERSION UPDATE")

    print(
        manager.evolve_version(
            item,
            "Improved validation"
        )
    )


    print("\n================")
    print("RESURRECT")

    item.state = "RETIRED"
    item.retirement_reason = "Decay"

    print(
        manager.resurrect(item)
    )


if __name__ == "__main__":
    run()
