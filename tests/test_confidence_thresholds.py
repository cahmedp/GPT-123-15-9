
"""
Dynamic Confidence Threshold Test
"""

from confidence.confidence_threshold_manager import (
    ConfidenceThresholdManager
)


def run():

    manager = ConfidenceThresholdManager()


    print("\n================")
    print("NORMAL")


    print(
        manager.evaluate(
            0.75,
            "NORMAL"
        )
    )


    print("\n================")
    print("CAUTIOUS")


    print(
        manager.evaluate(
            0.75,
            "CAUTIOUS"
        )
    )


    print("\n================")
    print("DEFENSIVE")


    print(
        manager.evaluate(
            0.86,
            "DEFENSIVE"
        )
    )


if __name__ == "__main__":
    run()
