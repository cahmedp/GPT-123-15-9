
from core.decision_trace_v2 import DecisionTraceBuilder
from core.production_runner_v1 import ProductionRunner


def run():

    print("\n================")
    print("TRACE")

    trace = DecisionTraceBuilder().create(
        "NZDCAD_021230",
        "BULLISH_EXPANSION",
        0.82,
        {
            "STRUCTURE":"ALIGN",
            "LIQUIDITY":"ALIGN",
            "LEARNING":"ABSTAIN"
        },
        "APPROVED",
        "BULLISH_EXPANSION_v2",
        "KNOWLEDGE_READY"
    )

    print(trace)


    print("\n================")
    print("RUNNER WAIT")


    class Adapter:
        def normalize(self, x):
            return x


    class Window:
        def __init__(self):
            self.n = 0

        def add(self, c):
            self.n += 1
            return {
                "ready": self.n >= 2,
                "size": self.n
            }


    runner = ProductionRunner(
        Adapter(),
        Window(),
        None,
        None,
        None
    )

    print(runner.process_candle({"close":100}))
    print(runner.process_candle({"close":101}))


if __name__ == "__main__":
    run()
