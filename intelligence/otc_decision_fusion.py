"""
OTC Decision Fusion 

Separates:
- Evidence strength
- Execution permission

No BUY/SELL generation.
"""

from dataclasses import dataclass


@dataclass
class FusionResult:
    state: str
    evidence_score: float
    execution_score: float
    execution_allowed: bool
    reason: str
    blockers: list


class OTCDecisionFusionV3:

    def evaluate(self, context):

        blockers = []

        if context.conflict_context.get("blocked"):
            blockers.append("HIGHER_TIMEFRAME_CONFLICT")

        if context.liquidity_context.get("blocked"):
            blockers.append(
                context.liquidity_context.get(
                    "state",
                    "LIQUIDITY_FAILURE"
                )
            )

        if context.candle_context.get("confirmed") is False:
            blockers.append("CANDLE_NOT_CONFIRMED")

        if context.temporal_context.get("state") in [
            "EXPIRED_OR_NOISY",
            "LATE_EXECUTION"
        ]:
            blockers.append("BAD_TIMING")

        evidence_score = self._evidence_score(context)

        execution_score = evidence_score

        # Execution penalties
        if "HIGHER_TIMEFRAME_CONFLICT" in blockers:
            execution_score *= 0.35

        if any("LIQUIDITY" in b for b in blockers):
            execution_score *= 0.25

        if "CANDLE_NOT_CONFIRMED" in blockers:
            execution_score *= 0.65

        if "BAD_TIMING" in blockers:
            execution_score *= 0.40

        execution_allowed = (
            execution_score >= 0.80
            and len(blockers) == 0
        )

        if execution_allowed:
            return FusionResult(
                "VALID_ENTRY",
                round(evidence_score, 3),
                round(execution_score, 3),
                True,
                "Evidence and execution conditions aligned",
                []
            )

        if blockers:
            return FusionResult(
                "WAIT",
                round(evidence_score, 3),
                round(execution_score, 3),
                False,
                "Execution blocked by evidence",
                blockers
            )

        if evidence_score >= 0.60:
            return FusionResult(
                "WAIT",
                round(evidence_score, 3),
                round(execution_score, 3),
                False,
                "Evidence incomplete",
                []
            )

        return FusionResult(
            "NO_EDGE",
            round(evidence_score, 3),
            round(execution_score, 3),
            False,
            "Weak evidence alignment",
            []
        )

    def _evidence_score(self, context):

        return (
            context.market_context.get("score", 0) * 0.20
            + context.setup_context.get("score", 0) * 0.20
            + context.micro_context.get("score", 0) * 0.15
            + context.pattern_context.get("score", 0) * 0.15
            + context.liquidity_context.get("score", 0) * 0.10
            + context.temporal_context.get("score", 0) * 0.20
        )
