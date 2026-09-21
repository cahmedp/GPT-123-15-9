import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from intelligence.otc_behavior_engine import OTCBehaviorEngine


def run_scenario(name, prices, context_5m, setup_1m):

    engine = OTCBehaviorEngine()
    profile = engine.analyze(prices)

    print("\n==============================")
    print(name)
    print("==============================")

    print("5M CONTEXT:", context_5m)
    print("1M SETUP:", setup_1m)
    print("30S OTC PROFILE:")
    print(profile.as_dict())


def build_prices(moves):
    price = 1.3000
    prices = []

    for move in moves:
        price += move * 0.00001
        prices.append(price)

    return prices


if __name__ == "__main__":

    scenarios = [

        (
            "5M BULL + 1M PULLBACK + 30S BUY PRESSURE",
            build_prices([1,1,1,-1,1,1,1] * 20),
            "BULLISH",
            "PULLBACK"
        ),

        (
            "5M BEAR + WEAK 1M BUY + 30S BUY",
            build_prices([-1,-1,-1,1,-1,1] * 20),
            "BEARISH",
            "WEAK_COUNTER_SETUP"
        ),

        (
            "5M RANGE + 1M RANGE + 30S CHOP",
            build_prices([1,-1,1,-1,1,-1] * 20),
            "RANGE",
            "RANGE"
        ),

        (
            "5M TREND + 30S REVERSAL RISK",
            build_prices([1,1,1,1,-1,-1,-1] * 20),
            "TRENDING",
            "REVERSAL"
        ),
    ]

    for scenario in scenarios:
        run_scenario(*scenario)
