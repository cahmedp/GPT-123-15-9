
from agents.candle_scenario_agent_v2 import CandleScenarioAgent
from validation.candle_quality_validator import CandleQualityValidator


def run():

    validator = CandleQualityValidator()

    agent = CandleScenarioAgent(
        "AGENT_1",
        validator
    )


    print("\n================")
    print("QUALITY PASS")


    candles = []

    for i in range(10):
        candles.append({
            "open":100+i,
            "close":101+i,
            "high":102+i,
            "low":99+i
        })


    print(
        agent.analyze(candles)
    )


    print("\n================")
    print("QUALITY BLOCK")


    candles = []

    for i in range(10):
        candles.append({
            "open":100,
            "close":100.1,
            "high":105,
            "low":95
        })


    print(
        agent.analyze(candles)
    )


if __name__ == "__main__":
    run()
