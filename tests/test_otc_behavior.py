import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from intelligence.otc_behavior_engine import OTCBehaviorEngine


def test_otc_debug_profile():

    prices = [
        1.33920,
        1.33921,
        1.33919,
        1.33923,
        1.33922,
        1.33925,
        1.33924,
        1.33928,
        1.33926,
        1.33930,
    ] * 12

    engine = OTCBehaviorEngine()

    profile = engine.analyze(prices)

    print("\n===== OTC DEBUG =====")
    print("samples:", profile.samples)
    print("first:", prices[0])
    print("last:", prices[-1])
    print("min:", min(prices))
    print("max:", max(prices))
    print("unique:", len(set(prices)))

    print(profile.as_dict())


if __name__ == "__main__":
    test_otc_debug_profile()