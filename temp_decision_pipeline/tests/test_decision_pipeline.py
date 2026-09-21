
"""
Decision Pipeline Test
"""

from pipeline.decision_pipeline import (
    DecisionPipelineCoordinator
)

from dataclasses import dataclass


@dataclass
class Threshold:
    decision: str


@dataclass
class Gate:
    allowed: bool


@dataclass
class Confidence:
    final_confidence: float


@dataclass
class Risk:
    blocked: bool


def run():

    pipeline = DecisionPipelineCoordinator()


    print("\n================")
    print("SUCCESS")


    print(
        pipeline.run(
            "ALIGNED",
            Confidence(0.86),
            Threshold("ALLOW"),
            Gate(True),
            Risk(False),
            trace="TRACE_OK"
        )
    )


    print("\n================")
    print("BLOCK")


    print(
        pipeline.run(
            "CONFLICT",
            Confidence(0.45),
            Threshold("BLOCK"),
            Gate(False),
            Risk(True),
            trace="TRACE_BLOCK"
        )
    )


if __name__ == "__main__":
    run()
