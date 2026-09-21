
from core.persistent_orchestrator_v1 import (
    PersistentOrchestrator
)


class Repo:

    def __init__(self):
        self.saved = []

    def save(self, item):
        self.saved.append(item)


def run():

    decision = Repo()
    knowledge = Repo()

    class Feedback:
        def save(self, *args):
            pass

    engine = PersistentOrchestrator(
        decision,
        knowledge,
        Feedback()
    )

    result = engine.finalize(
        "TRACE",
        "KNOWLEDGE",
        {
            "pattern":"BULLISH_EXPANSION",
            "prediction":"CALL",
            "actual":"CALL",
            "result":"MATCH",
            "reward":1
        }
    )

    print("\n================")
    print("PERSISTENT PIPELINE")

    print(result)


if __name__ == "__main__":
    run()
