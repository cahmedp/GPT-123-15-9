from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Any, Optional, Sequence

from config import CONFIG
from decision.decision_fusion import FusionDecision
from intelligence.regime_detector import RegimeSnapshot
from memory.memory_manager import MemoryCase, MemoryManager


@dataclass(frozen=True, slots=True)
class CalibratedDecision:
    """
    Advisory decision after confidence calibration.

    This remains an ANALYTICAL recommendation only.
    No order execution exists in this module.
    """

    timestamp: float
    asset: str
    price: float

    action: str                 # BUY | SELL | WAIT
    direction: str              # BULLISH | BEARISH | WAIT

    fusion_score: float

    raw_confidence: float
    calibrated_confidence: float
    confidence_adjustment: float

    uncertainty: float
    calibration_uncertainty: float

    historical_success_rate: Optional[float]
    historical_sample_size: int
    effective_sample_size: float

    calibration_error: Optional[float]
    calibration_method: str

    ready_for_risk_review: bool

    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "price": self.price,
            "action": self.action,
            "direction": self.direction,
            "fusion_score": self.fusion_score,
            "raw_confidence": self.raw_confidence,
            "calibrated_confidence": self.calibrated_confidence,
            "confidence_adjustment": self.confidence_adjustment,
            "uncertainty": self.uncertainty,
            "calibration_uncertainty": self.calibration_uncertainty,
            "historical_success_rate": self.historical_success_rate,
            "historical_sample_size": self.historical_sample_size,
            "effective_sample_size": self.effective_sample_size,
            "calibration_error": self.calibration_error,
            "calibration_method": self.calibration_method,
            "ready_for_risk_review": self.ready_for_risk_review,
            "reasons": list(self.reasons),
        }


class ConfidenceEngine:
    """
    Historical confidence calibration.

    Problem:
        A raw model confidence such as 0.80 is meaningless unless decisions
        historically made around that confidence actually succeed at roughly
        that rate.

    Method:
        - Read resolved historical MemoryCase records.
        - Prefer same asset + same direction + same regime.
        - Weight cases by closeness to the current raw confidence.
        - Estimate empirical success using Bayesian shrinkage.
        - Blend historical calibration with raw confidence according to sample
          strength.
        - Increase uncertainty when history is sparse or badly calibrated.

    Safety rules:
        - WAIT is never converted into BUY/SELL.
        - Calibration cannot bypass an earlier veto.
        - Small samples cannot create artificial high confidence.
        - No future/unresolved outcomes are used.
        - No order execution exists here.
    """

    PRIOR_ALPHA = 2.0
    PRIOR_BETA = 2.0

    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
    ) -> None:
        self.memory = memory or MemoryManager()

    def calibrate(
        self,
        *,
        decision: FusionDecision,
        regime: Optional[RegimeSnapshot] = None,
        max_history: int = 3000,
    ) -> CalibratedDecision:

        if max_history <= 0:
            raise ValueError(
                "max_history must be greater than zero."
            )

        # WAIT remains WAIT. Calibration only measures confidence; it never
        # creates a directional recommendation that did not already exist.
        if (
            decision.action == "WAIT"
            or decision.direction == "WAIT"
        ):
            reasons = [
                "raw decision is WAIT, so directional calibration is not applied",
            ]

            if decision.veto_active:
                reasons.append(
                    "an earlier safety veto remains active"
                )

            return CalibratedDecision(
                timestamp=decision.timestamp,
                asset=decision.asset,
                price=decision.price,

                action="WAIT",
                direction="WAIT",

                fusion_score=decision.fusion_score,

                raw_confidence=decision.raw_confidence,
                calibrated_confidence=0.0,
                confidence_adjustment=(
                    -decision.raw_confidence
                ),

                uncertainty=max(
                    decision.uncertainty,
                    0.75,
                ),
                calibration_uncertainty=1.0,

                historical_success_rate=None,
                historical_sample_size=0,
                effective_sample_size=0.0,

                calibration_error=None,
                calibration_method="wait_passthrough",

                ready_for_risk_review=False,

                reasons=tuple(reasons),
            )

        historical_cases = self._history(
            decision=decision,
            regime=regime,
            max_history=max_history,
        )

        estimate = self._calibration_estimate(
            raw_confidence=decision.raw_confidence,
            cases=historical_cases,
        )

        historical_success_rate = estimate[
            "success_rate"
        ]
        effective_sample_size = estimate[
            "effective_sample_size"
        ]
        historical_sample_size = len(
            historical_cases
        )

        calibration_error = self._calibration_error(
            historical_cases
        )

        sample_strength = self._clip01(
            effective_sample_size
            / max(
                CONFIG.LEARNING_MIN_VALIDATION_CASES,
                1,
            )
        )

        if historical_success_rate is None:
            calibrated = self._cold_start_confidence(
                decision.raw_confidence
            )
            method = "conservative_cold_start"
        else:
            calibrated = self._blend_confidence(
                raw_confidence=decision.raw_confidence,
                historical_rate=historical_success_rate,
                sample_strength=sample_strength,
            )
            method = "bayesian_local_empirical"

        # Confidence must not rise aggressively while historical calibration
        # remains uncertain.
        maximum_upward_adjustment = (
            CONFIG.LEARNING_MAX_WEIGHT_CHANGE_PER_UPDATE
            + 0.05 * sample_strength
        )

        calibrated = min(
            calibrated,
            decision.raw_confidence
            + maximum_upward_adjustment,
        )

        calibrated = self._clip01(
            calibrated
        )

        calibration_uncertainty = self._calibration_uncertainty(
            sample_strength=sample_strength,
            calibration_error=calibration_error,
            historical_rate=historical_success_rate,
        )

        combined_uncertainty = self._clip01(
            0.65 * decision.uncertainty
            + 0.35 * calibration_uncertainty
        )

        # Defensive mode threshold is applied later by RiskManager, but this
        # layer requires enough calibrated evidence before passing a
        # directional opinion forward.
        ready_for_risk_review = (
            decision.ready_for_confidence_calibration
            and calibrated
            >= CONFIG.MIN_ADVISORY_CONFIDENCE
            and combined_uncertainty
            <= CONFIG.MAX_UNCERTAINTY_FOR_DIRECTIONAL_ADVICE
        )

        reasons = self._build_reasons(
            decision=decision,
            calibrated=calibrated,
            historical_success_rate=historical_success_rate,
            historical_sample_size=historical_sample_size,
            effective_sample_size=effective_sample_size,
            calibration_error=calibration_error,
            sample_strength=sample_strength,
            calibration_uncertainty=calibration_uncertainty,
            combined_uncertainty=combined_uncertainty,
            ready_for_risk_review=ready_for_risk_review,
            regime=regime,
        )

        return CalibratedDecision(
            timestamp=decision.timestamp,
            asset=decision.asset,
            price=decision.price,

            action=decision.action,
            direction=decision.direction,

            fusion_score=decision.fusion_score,

            raw_confidence=float(
                decision.raw_confidence
            ),
            calibrated_confidence=float(
                calibrated
            ),
            confidence_adjustment=float(
                calibrated
                - decision.raw_confidence
            ),

            uncertainty=float(
                combined_uncertainty
            ),
            calibration_uncertainty=float(
                calibration_uncertainty
            ),

            historical_success_rate=(
                float(
                    historical_success_rate
                )
                if historical_success_rate
                is not None
                else None
            ),
            historical_sample_size=int(
                historical_sample_size
            ),
            effective_sample_size=float(
                effective_sample_size
            ),

            calibration_error=(
                float(
                    calibration_error
                )
                if calibration_error
                is not None
                else None
            ),
            calibration_method=method,

            ready_for_risk_review=bool(
                ready_for_risk_review
            ),

            reasons=tuple(reasons),
        )

    def _history(
        self,
        *,
        decision: FusionDecision,
        regime: Optional[RegimeSnapshot],
        max_history: int,
    ) -> list[MemoryCase]:
        cases = self.memory.recent_cases(
            limit=max_history,
            resolved_only=True,
            asset=decision.asset,
            timeframe_seconds=CONFIG.BASE_TIMEFRAME_SECONDS,
        )

        same_direction = [
            case
            for case in cases
            if case.direction
            == decision.direction
        ]

        if regime is None:
            return same_direction

        same_regime = [
            case
            for case in same_direction
            if case.regime
            == regime.primary_regime
        ]

        # Prefer matching-regime calibration when enough evidence exists.
        # Otherwise direction-only history is safer than pretending a tiny
        # regime sample is statistically strong.
        if (
            len(same_regime)
            >= max(
                25,
                CONFIG.LEARNING_MIN_NEW_CASES
                // 2,
            )
        ):
            return same_regime

        return same_direction

    def _calibration_estimate(
        self,
        *,
        raw_confidence: float,
        cases: Sequence[MemoryCase],
    ) -> dict[str, Optional[float]]:
        if not cases:
            return {
                "success_rate": None,
                "effective_sample_size": 0.0,
            }

        weighted_success = 0.0
        weight_total = 0.0
        squared_weight_total = 0.0

        bandwidth = 0.15

        for case in cases:
            if case.outcome_score is None:
                continue

            distance = abs(
                case.confidence
                - raw_confidence
            )

            # Gaussian-like local weighting around the current confidence.
            local_weight = exp(
                -(
                    distance
                    * distance
                )
                / (
                    2.0
                    * bandwidth
                    * bandwidth
                )
            )

            # More certain historical cases carry slightly more weight, while
            # even uncertain outcomes remain useful evidence.
            quality_weight = (
                0.50
                + 0.50
                * (
                    1.0
                    - case.uncertainty
                )
            )

            weight = (
                local_weight
                * quality_weight
            )

            if weight <= 0:
                continue

            success_value = (
                1.0
                if case.outcome_score > 0
                else 0.0
                if case.outcome_score < 0
                else 0.50
            )

            weighted_success += (
                success_value
                * weight
            )
            weight_total += weight
            squared_weight_total += (
                weight * weight
            )

        if weight_total <= 1e-12:
            return {
                "success_rate": None,
                "effective_sample_size": 0.0,
            }

        # Kish effective sample size for weighted observations.
        effective_sample_size = (
            (
                weight_total
                * weight_total
            )
            / max(
                squared_weight_total,
                1e-12,
            )
        )

        empirical_success = (
            weighted_success
            / weight_total
        )

        posterior_success = (
            (
                self.PRIOR_ALPHA
                + empirical_success
                * effective_sample_size
            )
            / (
                self.PRIOR_ALPHA
                + self.PRIOR_BETA
                + effective_sample_size
            )
        )

        return {
            "success_rate": self._clip01(
                posterior_success
            ),
            "effective_sample_size": float(
                effective_sample_size
            ),
        }

    @classmethod
    def _blend_confidence(
        cls,
        *,
        raw_confidence: float,
        historical_rate: float,
        sample_strength: float,
    ) -> float:
        """
        Sparse history -> mostly raw confidence, but conservative.
        Strong history -> empirical calibration gets more influence.
        """

        empirical_weight = (
            0.20
            + 0.60
            * sample_strength
        )

        raw_weight = (
            1.0
            - empirical_weight
        )

        estimate = (
            raw_weight
            * raw_confidence
            + empirical_weight
            * historical_rate
        )

        # Until sample strength is high, pull slightly toward 50%.
        shrinkage = (
            0.12
            * (
                1.0
                - sample_strength
            )
        )

        estimate = (
            estimate
            * (
                1.0
                - shrinkage
            )
            + 0.50
            * shrinkage
        )

        return cls._clip01(
            estimate
        )

    @staticmethod
    def _cold_start_confidence(
        raw_confidence: float,
    ) -> float:
        """
        No historical calibration yet.

        Preserve ranking but avoid pretending that a raw score is a proven
        probability.
        """

        return ConfidenceEngine._clip01(
            0.70
            * raw_confidence
            + 0.30
            * 0.50
        )

    @classmethod
    def _calibration_error(
        cls,
        cases: Sequence[MemoryCase],
        bins: int = 10,
    ) -> Optional[float]:
        """
        Expected Calibration Error (ECE)-style estimate.

        Each resolved historical case compares:
            stated confidence
            vs
            observed correctness
        """

        valid = [
            case
            for case in cases
            if case.outcome_score
            is not None
        ]

        if not valid:
            return None

        bins = max(
            int(bins),
            2,
        )

        total = len(valid)
        error = 0.0

        for bin_index in range(
            bins
        ):
            low = (
                bin_index
                / bins
            )

            high = (
                (
                    bin_index
                    + 1
                )
                / bins
            )

            if bin_index == bins - 1:
                group = [
                    case
                    for case in valid
                    if low
                    <= case.confidence
                    <= high
                ]
            else:
                group = [
                    case
                    for case in valid
                    if low
                    <= case.confidence
                    < high
                ]

            if not group:
                continue

            average_confidence = (
                sum(
                    case.confidence
                    for case in group
                )
                / len(group)
            )

            observed_success = (
                sum(
                    1.0
                    if case.outcome_score > 0
                    else 0.0
                    if case.outcome_score < 0
                    else 0.50
                    for case in group
                )
                / len(group)
            )

            error += (
                len(group)
                / total
            ) * abs(
                average_confidence
                - observed_success
            )

        return cls._clip01(
            error
        )

    @classmethod
    def _calibration_uncertainty(
        cls,
        *,
        sample_strength: float,
        calibration_error: Optional[float],
        historical_rate: Optional[float],
    ) -> float:
        sparse_component = (
            1.0
            - sample_strength
        )

        error_component = (
            calibration_error
            if calibration_error
            is not None
            else 0.50
        )

        missing_history = (
            1.0
            if historical_rate
            is None
            else 0.0
        )

        return cls._clip01(
            0.50
            * sparse_component
            + 0.35
            * error_component
            + 0.15
            * missing_history
        )

    @staticmethod
    def _build_reasons(
        *,
        decision: FusionDecision,
        calibrated: float,
        historical_success_rate: Optional[float],
        historical_sample_size: int,
        effective_sample_size: float,
        calibration_error: Optional[float],
        sample_strength: float,
        calibration_uncertainty: float,
        combined_uncertainty: float,
        ready_for_risk_review: bool,
        regime: Optional[RegimeSnapshot],
    ) -> list[str]:
        reasons: list[str] = [
            f"raw confidence={decision.raw_confidence:.2f}",
            f"calibrated confidence={calibrated:.2f}",
        ]

        if historical_success_rate is None:
            reasons.append(
                "historical calibration is not mature; conservative cold-start "
                "shrinkage was used"
            )
        else:
            reasons.append(
                f"local historical success estimate="
                f"{historical_success_rate:.2f}"
            )

        reasons.append(
            f"resolved calibration cases="
            f"{historical_sample_size}"
        )

        reasons.append(
            f"effective weighted sample="
            f"{effective_sample_size:.1f}"
        )

        if regime is not None:
            reasons.append(
                f"calibration context regime="
                f"{regime.primary_regime.lower()}"
            )

        if calibration_error is not None:
            reasons.append(
                f"historical calibration error="
                f"{calibration_error:.2f}"
            )

        if sample_strength < 0.50:
            reasons.append(
                "historical sample is not yet strong enough for aggressive "
                "confidence increases"
            )

        if (
            calibrated
            < decision.raw_confidence
        ):
            reasons.append(
                "historical evidence reduced the raw confidence"
            )
        elif (
            calibrated
            > decision.raw_confidence
        ):
            reasons.append(
                "historical evidence modestly increased confidence"
            )
        else:
            reasons.append(
                "calibration left confidence effectively unchanged"
            )

        reasons.append(
            f"calibration uncertainty="
            f"{calibration_uncertainty:.2f}"
        )

        reasons.append(
            f"combined uncertainty="
            f"{combined_uncertainty:.2f}"
        )

        if ready_for_risk_review:
            reasons.append(
                "calibrated decision is ready for the final risk review"
            )
        else:
            reasons.append(
                "confidence/uncertainty is not yet strong enough for a "
                "directional advisory call"
            )

        return reasons

    @staticmethod
    def _clip01(
        value: float,
    ) -> float:
        return min(
            max(
                float(value),
                0.0,
            ),
            1.0,
        )
