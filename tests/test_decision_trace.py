
"""
Decision Trace Test
"""

from observability.decision_trace import (
    DecisionTraceRecorder
)

from dataclasses import dataclass


@dataclass
class MockGate:
    allowed: bool
    blockers: list


def run():

    recorder = DecisionTraceRecorder()


    print("\n================")
    print("TRACE CREATION")


    trace = recorder.create(
        candle_id="NZDCAD_021230",
        asset="NZD/CAD",
        data_health=1.0,
        traders={
            "STRUCTURE":"ALIGN",
            "LIQUIDITY":"ALIGN",
            "LEARNING":"ABSTAIN"
        },
        knowledge_used=[
            "break_retest"
        ],
        consensus_score=0.86,
        consensus_confidence=0.78,
        gate_result=MockGate(
            True,
            []
        )
    )


    print(trace)


    print("\n================")
    print("EXPORT")


    print(
        recorder.export(trace)
    )


if __name__ == "__main__":
    run()
