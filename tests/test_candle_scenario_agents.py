
from agents.candle_scenario_agents import (
    CandleIntelligenceAgent,
    HybridPatternGenerator
)


def run():

    reports = []

    print("\n================")
    print("6 CANDLE AGENTS")


    for i in range(1, 7):

        agent = CandleIntelligenceAgent(
            f"AGENT_{i}"
        )

        for n in range(10):
            agent.add_candle({
                "close": 100 + n
            })

        report = agent.analyze()

        reports.append(report)

        print(report)


    print("\n================")
    print("HYBRID PATTERN")


    print(
        HybridPatternGenerator()
        .generate(reports)
    )


if __name__ == "__main__":
    run()
