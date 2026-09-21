from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True, slots=True)
class DecisionExplanation:
    """
    Human-readable explanation layer.

    Converts raw fusion/calibration outputs into a structured explanation.
    Advisory only. No execution logic.
    """

    action: str
    summary: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
    blockers: tuple[str, ...] = field(default_factory=tuple)
    metrics: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "summary": self.summary,
            "reasons": list(self.reasons),
            "blockers": list(self.blockers),
            "metrics": dict(self.metrics),
        }


class ExplanationEngine:
    """
    Builds an explanation from DecisionFusion and ConfidenceEngine results.

    This layer does not change decisions.
    It only explains why the system reached BUY / SELL / WAIT.
    """

    def explain(
        self,
        *,
        fusion_decision,
        calibrated_decision=None,
        risk_result: Optional[Any] = None,
    ) -> DecisionExplanation:

        reasons: list[str] = []
        blockers: list[str] = []

        action = getattr(fusion_decision, "action", "WAIT")

        reasons.extend(
            list(
                getattr(
                    fusion_decision,
                    "reasons",
                    (),
                )
            )
        )

        if calibrated_decision is not None:
            reasons.extend(
                list(
                    getattr(
                        calibrated_decision,
                        "reasons",
                        (),
                    )
                )
            )

        blocked_reason = getattr(
            fusion_decision,
            "blocked_reason",
            None,
        )

        if blocked_reason:
            blockers.append(str(blocked_reason))

        if risk_result is not None:
            risk_reason = getattr(
                risk_result,
                "blocked_reason",
                None,
            )
            if risk_reason:
                blockers.append(str(risk_reason))

        summary = self._build_summary(
            action=action,
            blockers=blockers,
        )

        metrics = {
            "fusion_score": getattr(
                fusion_decision,
                "fusion_score",
                None,
            ),
            "raw_confidence": getattr(
                fusion_decision,
                "raw_confidence",
                None,
            ),
            "uncertainty": getattr(
                fusion_decision,
                "uncertainty",
                None,
            ),
            "calibrated_confidence": (
                getattr(
                    calibrated_decision,
                    "calibrated_confidence",
                    None,
                )
                if calibrated_decision
                else None
            ),
        }

        return DecisionExplanation(
            action=action,
            summary=summary,
            reasons=tuple(reasons),
            blockers=tuple(blockers),
            metrics=metrics,
        )

    @staticmethod
    def _build_summary(
        *,
        action: str,
        blockers: list[str],
    ) -> str:

        if blockers:
            return (
                f"{action}: blocked by safety conditions"
            )

        if action == "BUY":
            return "BUY advisory generated after evidence fusion and validation"

        if action == "SELL":
            return "SELL advisory generated after evidence fusion and validation"

        return "WAIT advisory: evidence is not sufficient for directional call"
