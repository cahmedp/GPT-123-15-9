"""
Full OTC Brain Integration v2

Improvements:
1- Separate evidence score from execution permission.
2- Candle gate reduces confidence when candle is not closed.
3- Liquidity failure has explicit blocking state.
4- Unified result contract.

Flow:
5M Context
1M Setup
30S Execution
Pattern
Liquidity
Temporal
Candle
Fusion
"""

from dataclasses import dataclass


@dataclass
class DecisionResult:
    state: str
    evidence_score: float
    execution_allowed: bool
    reason: str


class OTCBrainFusionV2:

    def evaluate(
        self,
        context_5m,
        setup_1m,
        micro_30s,
        pattern_quality,
        liquidity_quality,
        temporal_quality,
        candle_confirmed,
        liquidity_failure,
        conflict,
    ):

        evidence_score = (
            0.20 * context_5m
            + 0.20 * setup_1m
            + 0.15 * micro_30s
            + 0.15 * pattern_quality
            + 0.10 * liquidity_quality
            + 0.20 * temporal_quality
        )

        # Hard blockers
        if liquidity_failure:
            return DecisionResult(
                "BLOCKED_LIQUIDITY_FAILURE",
                round(evidence_score, 3),
                False,
                "Liquidity behavior invalidated the setup"
            )

        if conflict:
            return DecisionResult(
                "WAIT",
                round(evidence_score, 3),
                False,
                "Conflict detected between layers"
            )

        if not candle_confirmed:
            adjusted_score = min(evidence_score, 0.70)

            return DecisionResult(
                "WAIT",
                round(adjusted_score, 3),
                False,
                "Waiting candle confirmation"
            )

        if evidence_score >= 0.80:
            return DecisionResult(
                "VALID_ENTRY",
                round(evidence_score, 3),
                True,
                "All evidence layers aligned"
            )

        if evidence_score >= 0.60:
            return DecisionResult(
                "WAIT",
                round(evidence_score, 3),
                False,
                "Evidence incomplete"
            )

        return DecisionResult(
            "NO_EDGE",
            round(evidence_score, 3),
            False,
            "Weak alignment"
        )


if __name__ == "__main__":

    engine = OTCBrainFusionV2()

    cases = [
        (
            "Complete aligned continuation",
            0.90, 0.85, 0.85,
            0.84, 0.88, 0.878,
            True, False, False
        ),
        (
            "Good setup candle open",
            0.90, 0.85, 0.85,
            0.84, 0.88, 0.878,
            False, False, False
        ),
        (
            "Fake breakout liquidity failure",
            0.60, 0.50, 0.40,
            0.45, 0.35, 0.60,
            True, True, False
        ),
        (
            "Multi layer conflict",
            0.90, 0.40, 0.70,
            0.80, 0.70, 0.80,
            True, False, True
        ),
    ]

    for case in cases:
        print("\n================")
        print(case[0])
        print(
            engine.evaluate(*case[1:])
        )
