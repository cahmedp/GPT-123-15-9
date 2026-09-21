import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from intelligence.otc_behavior_engine import OTCBehaviorEngine


def run_case(name, prices):
    engine = OTCBehaviorEngine()
    profile = engine.analyze(prices)

    print("\n======================")
    print(name)
    print("======================")
    print(profile.as_dict())


def test_bullish_micro_pressure():
    prices = []
    price = 1.3000

    moves = [
        1, 1, 1, -1, 1, 1, 1, 1,
        -1, 1, 1, 1
    ]

    for move in moves * 10:
        price += move * 0.00001
        prices.append(price)

    run_case("BULLISH MICRO PRESSURE", prices)


def test_bearish_micro_pressure():
    prices = []
    price = 1.3000

    moves = [
        -1, -1, -1, 1, -1, -1,
        -1, -1, 1, -1, -1
    ]

    for move in moves * 10:
        price += move * 0.00001
        prices.append(price)

    run_case("BEARISH MICRO PRESSURE", prices)


def test_otc_choppy_noise():
    prices = []
    price = 1.3000

    moves = [1, -1, 1, -1, 1, -1]

    for move in moves * 20:
        price += move * 0.00001
        prices.append(price)

    run_case("CHOPPY OTC NOISE", prices)


def test_fake_breakout_reversal():
    prices = []
    price = 1.3000

    moves = [1, 1, 1, 1, 1, -1, -1, -1]

    for move in moves * 15:
        price += move * 0.00001
        prices.append(price)

    run_case("FAKE BREAKOUT REVERSAL", prices)


if __name__ == "__main__":
    test_bullish_micro_pressure()
    test_bearish_micro_pressure()
    test_otc_choppy_noise()
    test_fake_breakout_reversal()
