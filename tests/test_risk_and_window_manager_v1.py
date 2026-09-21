
from risk.risk_decision_layer_v1 import RiskDecisionEngine
from candle.live_window_manager_v1 import CandleWindowManager


class Data:
    valid = True


class Confidence:
    confidence = 0.86


def run():

    print("\n================")
    print("WINDOW")

    manager = CandleWindowManager(3)

    for i in range(3):
        print(
            manager.add(
                {"close":100+i}
            )
        )


    print("\n================")
    print("RISK APPROVED")

    print(
        RiskDecisionEngine().evaluate(
            Data(),
            Confidence(),
            "NO_CONFLICT"
        )
    )


    print("\n================")
    print("RISK BLOCK")

    print(
        RiskDecisionEngine().evaluate(
            Data(),
            type(
                "C",
                (),
                {"confidence":0.4}
            )(),
            "HIGH_CONFLICT"
        )
    )


if __name__ == "__main__":
    run()
