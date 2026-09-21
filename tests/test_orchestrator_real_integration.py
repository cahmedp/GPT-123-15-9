"""
Real Orchestrator Integration Test

Purpose:
Validate the real integration point between:

Decision Pipeline
        |
        v
Microstructure Observer Hook

Rules:
- Observer is optional.
- Decision result must remain unchanged.
- Observer failure must be isolated.

This is a safe integration template before modifying
the production orchestrator.
"""


class RealOrchestratorTestDouble:

    def __init__(self, observer=None):

        self.observer = observer


    def execute_pipeline(self):

        # Simulated result coming from Decision Fusion

        decision_result = {
            "state": "VALID_ENTRY",
            "execution_allowed": True,
            "score": 0.867
        }


        if self.observer:

            try:

                self.observer.on_decision(
                    decision_result
                )

                decision_result["observer_status"] = "OK"

            except Exception as error:

                decision_result["observer_status"] = "FAILED"
                decision_result["observer_error"] = str(error)


        return decision_result



class WorkingObserver:

    def on_decision(self, decision):

        return {
            "snapshot": "created"
        }



class BrokenObserver:

    def on_decision(self, decision):

        raise RuntimeError(
            "microstructure memory unavailable"
        )



def run():

    print("\n================")
    print("REAL INTEGRATION - OBSERVER ACTIVE")

    orchestrator = RealOrchestratorTestDouble(
        observer=WorkingObserver()
    )

    print(
        orchestrator.execute_pipeline()
    )


    print("\n================")
    print("REAL INTEGRATION - OBSERVER FAILURE")

    orchestrator = RealOrchestratorTestDouble(
        observer=BrokenObserver()
    )

    print(
        orchestrator.execute_pipeline()
    )


    print("\n================")
    print("NO OBSERVER MODE")

    orchestrator = RealOrchestratorTestDouble(
        observer=None
    )

    print(
        orchestrator.execute_pipeline()
    )


if __name__ == "__main__":
    run()
