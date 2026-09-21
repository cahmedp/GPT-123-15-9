
"""
Regime Weighting Test
"""

from learning.regime_weight_manager import (
    RegimeWeightManager
)


def run():

    manager = RegimeWeightManager()


    print("\n================")
    print("EXPANSION REGIME")


    for _ in range(90):
        manager.update(
            "structure",
            "EXPANSION",
            True
        )

    for _ in range(10):
        manager.update(
            "structure",
            "EXPANSION",
            False
        )

    print(
        manager.get_weight(
            "structure",
            "EXPANSION"
        )
    )


    print("\n================")
    print("RANGE REGIME")


    for _ in range(60):
        manager.update(
            "structure",
            "RANGE",
            False
        )

    for _ in range(40):
        manager.update(
            "structure",
            "RANGE",
            True
        )


    print(
        manager.get_weight(
            "structure",
            "RANGE"
        )
    )


if __name__ == "__main__":
    run()
