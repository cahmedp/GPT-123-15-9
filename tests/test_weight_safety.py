
"""
Weight Safety Guard Test
"""

from learning.weight_safety_guard import (
    WeightSafetyGuard
)


def run():

    guard = WeightSafetyGuard(
        min_samples=30,
        max_change=0.10
    )


    print("\n================")
    print("SMALL SAMPLE")


    print(
        guard.apply(
            0.50,
            0.90,
            5
        )
    )


    print("\n================")
    print("LARGE SUDDEN JUMP")


    print(
        guard.apply(
            0.50,
            0.90,
            100
        )
    )


    print("\n================")
    print("NORMAL UPDATE")


    print(
        guard.apply(
            0.70,
            0.76,
            100
        )
    )


if __name__ == "__main__":
    run()
