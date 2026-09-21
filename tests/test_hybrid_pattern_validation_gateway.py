
from validation.hybrid_pattern_validation_gateway import (
    HybridPatternValidationGateway
)


class Confidence:
    def __init__(self, confidence, status):
        self.confidence = confidence
        self.status = status


def run():

    gateway = HybridPatternValidationGateway()


    print("\n================")
    print("VALIDATED HYBRID")


    print(
        gateway.validate(
            "BULLISH_EXPANSION",
            Confidence(0.80, "STRONG_HYBRID"),
            "SUPPORTED",
            {"success_rate":0.78},
            "FORWARD_VALIDATED"
        )
    )


    print("\n================")
    print("BLOCKED HYBRID")


    print(
        gateway.validate(
            "BULLISH_EXPANSION",
            Confidence(0.50, "CAUTIOUS_HYBRID"),
            "FAILED",
            {"success_rate":0.40},
            "FAILED_FORWARD_TEST"
        )
    )


if __name__ == "__main__":
    run()
