"""
Observer Failure Isolation Test

Rule:
Observer / Learning layer failure
must NOT break live decision flow.

Expected:
Decision remains available.
Observer failure is isolated.
"""


class FakeDecision:
    def __init__(self):
        self.state = "VALID_ENTRY"
        self.execution_allowed = True


class FailingObserver:

    def on_decision(self, *args, **kwargs):
        raise RuntimeError("Observer storage failure")


def safe_notify(observer, decision):

    try:
        observer.on_decision(decision)
        return {
            "observer_status": "OK",
            "decision_preserved": True
        }

    except Exception as error:

        return {
            "observer_status": "FAILED",
            "error": str(error),
            "decision_preserved": True
        }


def run():

    decision = FakeDecision()
    observer = FailingObserver()

    print("\n================")
    print("LIVE DECISION BEFORE OBSERVER")

    print({
        "state": decision.state,
        "execution_allowed": decision.execution_allowed
    })


    print("\n================")
    print("OBSERVER FAILURE")

    result = safe_notify(
        observer,
        decision
    )

    print(result)


    print("\n================")
    print("LIVE DECISION AFTER OBSERVER FAILURE")

    print({
        "state": decision.state,
        "execution_allowed": decision.execution_allowed
    })


if __name__ == "__main__":
    run()
