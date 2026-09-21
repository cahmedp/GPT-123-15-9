
from agents.six_candle_agents_quality_gate import (
    SixCandleAgentsQualityGate
)
from validation.candle_quality_validator import (
    CandleQualityValidator
)


def make_good():
    return [
        {
            "open":100+i,
            "close":101+i,
            "high":102+i,
            "low":99+i
        }
        for i in range(10)
    ]


def make_bad():
    return [
        {
            "open":100,
            "close":100.1,
            "high":105,
            "low":95
        }
        for _ in range(10)
    ]


def run():

    system = SixCandleAgentsQualityGate(
        CandleQualityValidator()
    )

    windows = {
        "AGENT_1": make_good(),
        "AGENT_2": make_good(),
        "AGENT_3": make_bad(),
        "AGENT_4": make_good(),
        "AGENT_5": make_good(),
        "AGENT_6": make_bad(),
    }

    print("\n================")
    print("AGENT REPORTS")

    reports = system.analyze_agents(windows)

    for r in reports:
        print(r)


    print("\n================")
    print("HYBRID PATTERN")

    print(
        system.build_hybrid_pattern(reports)
    )


if __name__ == "__main__":
    run()
