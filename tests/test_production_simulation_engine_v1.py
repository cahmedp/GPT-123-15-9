
from simulation.production_simulation_engine_v1 import (
    ProductionSimulationEngine
)


class Pipeline:

    def process(self, candle):

        class Result:
            pass

        r = Result()

        if candle["ok"]:
            r.stage = "EXECUTION_READY"
            r.confidence = 0.82
            r.blockers = []
        else:
            r.stage = "RISK_BLOCK"
            r.confidence = 0.4
            r.blockers = [
                "LOW_CONFIDENCE"
            ]

        return r


def run():

    engine = ProductionSimulationEngine(
        Pipeline()
    )

    report = engine.run(
        [
            {"ok":True},
            {"ok":True},
            {"ok":False},
            {"ok":True}
        ]
    )

    print("\n================")
    print("SIMULATION REPORT")
    print(report)


if __name__ == "__main__":
    run()
