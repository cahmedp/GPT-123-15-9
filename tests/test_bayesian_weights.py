
"""
Bayesian Weight Manager Test
"""


from learning.bayesian_weight_manager import (
    BayesianWeightManager
)


def run():

    manager = BayesianWeightManager()


    print("\n================")
    print("SMALL SAMPLE PROTECTION")


    manager.update(
        "structure",
        True
    )


    print(
        manager.get_weight(
            "structure"
        )
    )


    print("\n================")
    print("LARGE SAMPLE")


    for _ in range(80):
        manager.update(
            "liquidity",
            True
        )

    for _ in range(20):
        manager.update(
            "liquidity",
            False
        )


    print(
        manager.get_weight(
            "liquidity"
        )
    )


if __name__ == "__main__":
    run()
