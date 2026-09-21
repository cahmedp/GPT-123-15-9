
"""
Consensus Decision Gate Test
"""

from decision.consensus_decision_gate import (
    ConsensusDecisionGate
)

from dataclasses import dataclass


@dataclass
class MockConfidence:
    confidence: float
    status: str


def run():

    gate = ConsensusDecisionGate()


    print("\n================")
    print("VALID PATH")


    print(
        gate.evaluate(
            MockConfidence(
                0.86,
                "RELIABLE_CONSENSUS"
            ),
            data_health=1.0,
            microstructure_valid=True,
            risk_blocked=False
        )
    )


    print("\n================")
    print("WEAK CONSENSUS")


    print(
        gate.evaluate(
            MockConfidence(
                0.53,
                "WEAK_CONSENSUS"
            ),
            data_health=1.0,
            microstructure_valid=True,
            risk_blocked=False
        )
    )


    print("\n================")
    print("MULTI BLOCK")


    print(
        gate.evaluate(
            MockConfidence(
                0.90,
                "RELIABLE_CONSENSUS"
            ),
            data_health=0.40,
            microstructure_valid=False,
            risk_blocked=True
        )
    )


if __name__ == "__main__":
    run()
