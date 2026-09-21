
"""
Adaptive Confidence Test
"""

from confidence.adaptive_confidence_controller import (
    AdaptiveConfidenceController
)


def run():

    controller = AdaptiveConfidenceController()


    print("\n================")
    print("HEALTHY MARKET")


    print(
        controller.calculate(
            consensus_confidence=0.86,
            market_multiplier=1.0,
            knowledge_reliability=0.82,
            calibration_factor=0.90
        )
    )


    print("\n================")
    print("STERILE MARKET")


    print(
        controller.calculate(
            consensus_confidence=0.86,
            market_multiplier=0.55,
            knowledge_reliability=0.82,
            calibration_factor=0.90
        )
    )


if __name__ == "__main__":
    run()
