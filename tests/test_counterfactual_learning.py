
"""
Counterfactual Learning Test
"""

from learning.counterfactual_store import (
    CounterfactualStore
)


def run():

    store = CounterfactualStore()


    print("\n================")
    print("RECORD NO TRADE")


    event = store.record_no_trade(
        "NZDCAD_021230",
        "CANDLE_NOT_CONFIRMED"
    )

    print(event)


    print("\n================")
    print("EVALUATE FUTURE")


    result = store.evaluate(
        "NZDCAD_021230",
        "MATCH"
    )

    print(result)


    print("\n================")
    print("MEMORY")


    print(
        store.all()
    )


if __name__ == "__main__":
    run()
