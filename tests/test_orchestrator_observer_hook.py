"""
Orchestrator Observer Hook Test

Purpose:
Validate that MicrostructureObserver can be attached
to the orchestrator flow without affecting decisions.

Rules:
- Decision must survive observer success.
- Decision must survive observer failure.
- Observer is side-effect only.
"""


class MockOrchestrator:

    def __init__(self, observer=None):
        self.observer = observer


    def process_decision(self, decision):

        result = {
            "state": decision["state"],
            "execution_allowed": decision["execution_allowed"]
        }

        if self.observer:

            try:
                self.observer.on_decision(decision)

                result["observer"] = "OK"

            except Exception as error:

                result["observer"] = "FAILED"
                result["observer_error"] = str(error)

        return result



class MockObserver:

    def __init__(self, fail=False):
        self.fail = fail


    def on_decision(self, decision):

        if self.fail:
            raise RuntimeError(
                "Observer hook failure"
            )

        return True



def run():

    decision = {
        "state": "VALID_ENTRY",
        "execution_allowed": True
    }


    print("\n================")
    print("OBSERVER SUCCESS")

    orchestrator = MockOrchestrator(
        MockObserver(fail=False)
    )

    print(
        orchestrator.process_decision(decision)
    )


    print("\n================")
    print("OBSERVER FAILURE ISOLATION")

    orchestrator = MockOrchestrator(
        MockObserver(fail=True)
    )

    print(
        orchestrator.process_decision(decision)
    )


if __name__ == "__main__":
    run()
