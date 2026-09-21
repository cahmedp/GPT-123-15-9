
from performance.performance_intelligence_engine_v1 import (
    PerformanceIntelligenceEngine
)


def run():

    engine = PerformanceIntelligenceEngine()

    report = engine.generate_report()

    print("\n================")
    print("PERFORMANCE REPORT")

    print(report)


if __name__ == "__main__":
    run()
