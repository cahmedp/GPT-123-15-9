
from knowledge.promotion_lifecycle_v2 import (
    KnowledgePromotionLifecycle
)


def run():

    manager = KnowledgePromotionLifecycle()

    print("\n================")
    print("CREATE")

    item = manager.create(
        "BULLISH_EXPANSION",
        0.82
    )

    print(item)


    print("\n================")
    print("PROMOTION")

    print(
        manager.promote(
            item,
            True
        )
    )


    print("\n================")
    print("DECAY")

    print(
        manager.update_performance(
            item,
            0.4
        )
    )


    print("\n================")
    print("RETIRE")

    print(
        manager.retire(
            item,
            "Performance degraded"
        )
    )


if __name__ == "__main__":
    run()
