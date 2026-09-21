from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from agents.analyst_coordinator import AgentDebateSnapshot
from config import CONFIG
from decision.confidence_engine import CalibratedDecision
from intelligence.market_intelligence import MarketIntelligenceSnapshot
from intelligence.regime_detector import RegimeSnapshot
from simulation.scenario_engine import ScenarioSimulationResult


@dataclass(frozen=True, slots=True)
class FinalRiskDecision:
    """
    Final advisory gate.

    advisory_action:
        BUY | SELL | WAIT

    This object is intended for UI/reporting only.
    It never sends or executes a Pocket Option order.
    """

    timestamp: float
    asset: str
    price: float

    advisory_action: str
    direction: str

    calibrated_confidence: float
    required_confidence: float

    risk_score: float
    uncertainty: float
    data_risk: float
    market_risk: float
    model_risk: float
    behavioral_risk: float

    signal_strength: str

    blocked: bool
    block_reasons: tuple[str, ...]

    reasons: tuple[str, ...] = field(default_factory=tuple)
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "price": self.price,
            "advisory_action": self.advisory_action,
            "direction": self.direction,
            "calibrated_confidence": self.calibrated_confidence,
            "required_confidence": self.required_confidence,
            "risk_score": self.risk_score,
            "uncertainty": self.uncertainty,
            "data_risk": self.data_risk,
            "market_risk": self.market_risk,
            "model_risk": self.model_risk,
            "behavioral_risk": self.behavioral_risk,
            "signal_strength": self.signal_strength,
            "blocked": self.blocked,
            "block_reasons": list(self.block_reasons),
            "reasons": list(self.reasons),
            "evidence": dict(self.evidence),
        }


class RiskManager:
    """
    Independent final safety gate.

    It reviews:
        - calibrated confidence,
        - total uncertainty,
        - market noise/conflict,
        - regime instability,
        - agent veto/disagreement,
        - scenario failure probability,
        - stale/reconnecting data,
        - defensive mode after repeated bad outcomes.

    Safety principle:
        An earlier WAIT is never upgraded into BUY/SELL.

    This module provides analysis only and does not execute trades.
    """

    def review(
        self,
        *,
        decision: CalibratedDecision,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        simulation: Optional[ScenarioSimulationResult] = None,
        session_context: Optional[Mapping[str, Any]] = None,
    ) -> FinalRiskDecision:
        session_context = session_context or {}

        data_risk = self._data_risk(
            session_context
        )

        market_risk = self._market_risk(
            market=market,
            regime=regime,
        )

        model_risk = self._model_risk(
            decision=decision,
            debate=debate,
            simulation=simulation,
        )

        behavioral_risk = self._behavioral_risk(
            session_context
        )

        risk_score = self._clip01(
            0.24 * data_risk
            + 0.32 * market_risk
            + 0.30 * model_risk
            + 0.14 * behavioral_risk
        )

        required_confidence = self._required_confidence(
            session_context=session_context,
            risk_score=risk_score,
        )

        block_reasons = self._block_reasons(
            decision=decision,
            market=market,
            regime=regime,
            debate=debate,
            simulation=simulation,
            data_risk=data_risk,
            market_risk=market_risk,
            model_risk=model_risk,
            behavioral_risk=behavioral_risk,
            risk_score=risk_score,
            required_confidence=required_confidence,
            session_context=session_context,
        )

        blocked = bool(
            block_reasons
        )

        if (
            blocked
            or decision.action == "WAIT"
            or decision.direction == "WAIT"
        ):
            advisory_action = "WAIT"
            direction = "WAIT"
        else:
            advisory_action = decision.action
            direction = decision.direction

        signal_strength = self._signal_strength(
            action=advisory_action,
            confidence=decision.calibrated_confidence,
            risk_score=risk_score,
        )

        reasons = self._build_reasons(
            advisory_action=advisory_action,
            decision=decision,
            market=market,
            regime=regime,
            debate=debate,
            simulation=simulation,
            risk_score=risk_score,
            required_confidence=required_confidence,
            data_risk=data_risk,
            market_risk=market_risk,
            model_risk=model_risk,
            behavioral_risk=behavioral_risk,
            signal_strength=signal_strength,
            block_reasons=block_reasons,
        )

        evidence = {
            "market_readiness": market.readiness_state,
            "market_quality": round(
                market.market_quality,
                6,
            ),
            "market_noise": round(
                market.noise_score,
                6,
            ),
            "market_conflict": round(
                market.conflict_score,
                6,
            ),
            "regime": regime.primary_regime,
            "regime_confidence": round(
                regime.regime_confidence,
                6,
            ),
            "regime_transition_strength": round(
                regime.transition_strength,
                6,
            ),
            "agent_consensus": debate.consensus_direction,
            "agent_disagreement": round(
                debate.disagreement_score,
                6,
            ),
            "agent_veto": debate.veto_active,
            "calibration_method": decision.calibration_method,
            "historical_sample_size": (
                decision.historical_sample_size
            ),
            "effective_sample_size": round(
                decision.effective_sample_size,
                6,
            ),
            "defensive_mode": bool(
                session_context.get(
                    "defensive_mode",
                    False,
                )
            ),
            "consecutive_bad_outcomes": self._safe_int(
                session_context.get(
                    "consecutive_bad_outcomes",
                    0,
                )
            ),
            "data_stale": bool(
                session_context.get(
                    "data_stale",
                    False,
                )
            ),
        }

        if simulation is not None:
            evidence.update(
                {
                    "simulation_usable": (
                        simulation.usable_for_fusion
                    ),
                    "simulation_confidence": round(
                        simulation.simulation_confidence,
                        6,
                    ),
                    "simulation_failure_probability": round(
                        simulation.failure_probability,
                        6,
                    ),
                    "simulation_disagreement": round(
                        simulation.scenario_disagreement,
                        6,
                    ),
                }
            )

        return FinalRiskDecision(
            timestamp=float(
                decision.timestamp
            ),
            asset=decision.asset,
            price=float(
                decision.price
            ),

            advisory_action=advisory_action,
            direction=direction,

            calibrated_confidence=float(
                decision.calibrated_confidence
            ),
            required_confidence=float(
                required_confidence
            ),

            risk_score=float(
                risk_score
            ),
            uncertainty=float(
                decision.uncertainty
            ),
            data_risk=float(
                data_risk
            ),
            market_risk=float(
                market_risk
            ),
            model_risk=float(
                model_risk
            ),
            behavioral_risk=float(
                behavioral_risk
            ),

            signal_strength=signal_strength,

            blocked=blocked,
            block_reasons=tuple(
                block_reasons
            ),

            reasons=tuple(
                reasons
            ),
            evidence=evidence,
        )

    @classmethod
    def _data_risk(
        cls,
        context: Mapping[str, Any],
    ) -> float:
        risk = 0.0

        if bool(
            context.get(
                "data_stale",
                False,
            )
        ):
            risk = 1.0

        seconds_since_tick = cls._safe_float(
            context.get(
                "seconds_since_last_tick",
                0.0,
            )
        )

        stale_after = max(
            cls._config_float(
                "DATA_STALE_AFTER_SECONDS",
                8.0,
            ),
            1e-9,
        )

        if seconds_since_tick > 0:
            risk = max(
                risk,
                cls._clip01(
                    seconds_since_tick
                    / stale_after
                ),
            )

        data_quality = context.get(
            "data_quality_score"
        )

        if data_quality is not None:
            risk = max(
                risk,
                1.0
                - cls._clip01(
                    cls._safe_float(
                        data_quality,
                        0.0,
                    )
                ),
            )

        reconnect_count = cls._safe_int(
            context.get(
                "reconnect_count",
                0,
            )
        )

        if reconnect_count > 0:
            risk = max(
                risk,
                min(
                    reconnect_count
                    / 10.0,
                    0.70,
                ),
            )

        return cls._clip01(
            risk
        )

    @classmethod
    def _market_risk(
        cls,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
    ) -> float:
        readiness = {
            "READY": 0.05,
            "OBSERVE": 0.30,
            "WAIT_LOW_QUALITY": 0.70,
            "WAIT_CONFLICT": 0.85,
            "BLOCKED_NOISE": 1.00,
            "WARMUP": 1.00,
        }.get(
            market.readiness_state,
            0.55,
        )

        regime_risk = {
            "BULLISH_TREND": 0.15,
            "BEARISH_TREND": 0.15,
            "BULLISH_EXPANSION": 0.30,
            "BEARISH_EXPANSION": 0.30,
            "RANGE": 0.50,
            "COMPRESSION": 0.50,
            "TRANSITION": 0.80,
            "HIGH_NOISE": 1.00,
        }.get(
            regime.primary_regime,
            0.55,
        )

        return cls._clip01(
            0.25
            * market.noise_score
            + 0.20
            * market.conflict_score
            + 0.15
            * (
                1.0
                - market.market_quality
            )
            + 0.15
            * regime.transition_strength
            + 0.10
            * regime_risk
            + 0.15
            * readiness
        )

    @classmethod
    def _model_risk(
        cls,
        *,
        decision: CalibratedDecision,
        debate: AgentDebateSnapshot,
        simulation: Optional[ScenarioSimulationResult],
    ) -> float:
        calibration_risk = cls._clip01(
            decision.calibration_uncertainty
        )

        disagreement = cls._clip01(
            debate.disagreement_score
        )

        uncertainty = cls._clip01(
            decision.uncertainty
        )

        veto_risk = (
            1.0
            if debate.veto_active
            else 0.0
        )

        if simulation is None:
            simulation_risk = 0.55
        else:
            simulation_risk = cls._clip01(
                0.45
                * simulation.failure_probability
                + 0.35
                * simulation.scenario_disagreement
                + 0.20
                * (
                    1.0
                    - simulation.simulation_confidence
                )
            )

        return cls._clip01(
            0.25
            * calibration_risk
            + 0.25
            * uncertainty
            + 0.20
            * disagreement
            + 0.20
            * simulation_risk
            + 0.10
            * veto_risk
        )

    @classmethod
    def _behavioral_risk(
        cls,
        context: Mapping[str, Any],
    ) -> float:
        if bool(
            context.get(
                "defensive_mode",
                False,
            )
        ):
            return 1.0

        bad = cls._safe_int(
            context.get(
                "consecutive_bad_outcomes",
                0,
            )
        )

        threshold = max(
            cls._config_int(
                "MAX_CONSECUTIVE_BAD_OUTCOMES",
                3,
            ),
            1,
        )

        return cls._clip01(
            bad / threshold
        )

    @classmethod
    def _required_confidence(
        cls,
        *,
        session_context: Mapping[str, Any],
        risk_score: float,
    ) -> float:
        base = cls._config_float(
            "MIN_ADVISORY_CONFIDENCE",
            0.68,
        )

        defensive_bonus = (
            cls._config_float(
                "DEFENSIVE_MODE_CONFIDENCE_BONUS",
                0.08,
            )
            if bool(
                session_context.get(
                    "defensive_mode",
                    False,
                )
            )
            else 0.0
        )

        risk_bonus = (
            0.10
            * cls._clip01(
                risk_score
            )
        )

        return cls._clip01(
            base
            + defensive_bonus
            + risk_bonus
        )

    @classmethod
    def _block_reasons(
        cls,
        *,
        decision: CalibratedDecision,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        simulation: Optional[ScenarioSimulationResult],
        data_risk: float,
        market_risk: float,
        model_risk: float,
        behavioral_risk: float,
        risk_score: float,
        required_confidence: float,
        session_context: Mapping[str, Any],
    ) -> list[str]:
        reasons: list[str] = []

        if (
            decision.action == "WAIT"
            or decision.direction == "WAIT"
        ):
            reasons.append(
                "upstream decision is WAIT"
            )

        if not decision.ready_for_risk_review:
            reasons.append(
                "calibrated decision is not ready for final risk review"
            )

        if debate.veto_active:
            reasons.append(
                "multi-agent safety veto is active"
            )

        if market.readiness_state in {
            "WARMUP",
            "BLOCKED_NOISE",
        }:
            reasons.append(
                f"market readiness blocks directional advice: "
                f"{market.readiness_state.lower()}"
            )

        if regime.primary_regime == "HIGH_NOISE":
            reasons.append(
                "high-noise regime blocks directional advice"
            )

        if bool(
            session_context.get(
                "data_stale",
                False,
            )
        ):
            reasons.append(
                "live market data is stale"
            )

        if data_risk >= 0.75:
            reasons.append(
                "data reliability risk is too high"
            )

        if (
            market.noise_score
            >= cls._config_float(
                "HIGH_NOISE_BLOCK_THRESHOLD",
                0.75,
            )
        ):
            reasons.append(
                "market noise exceeds safety threshold"
            )

        if (
            decision.uncertainty
            > cls._config_float(
                "MAX_UNCERTAINTY_FOR_DIRECTIONAL_ADVICE",
                0.35,
            )
        ):
            reasons.append(
                "decision uncertainty exceeds allowed threshold"
            )

        if (
            decision.calibrated_confidence
            < required_confidence
        ):
            reasons.append(
                "calibrated confidence is below the required threshold"
            )

        if (
            debate.disagreement_score
            > cls._config_float(
                "AGENT_CONFLICT_THRESHOLD",
                0.35,
            )
        ):
            reasons.append(
                "agent disagreement exceeds allowed threshold"
            )

        if (
            simulation is not None
            and simulation.failure_probability
            > 0.60
        ):
            reasons.append(
                "scenario failure probability is too high"
            )

        if (
            simulation is not None
            and simulation.scenario_disagreement
            > 0.80
        ):
            reasons.append(
                "future scenarios disagree too strongly"
            )

        if market_risk >= 0.80:
            reasons.append(
                "market risk is too high"
            )

        if model_risk >= 0.80:
            reasons.append(
                "model uncertainty risk is too high"
            )

        if behavioral_risk >= 1.0:
            reasons.append(
                "defensive mode blocks new directional advice"
            )

        if (
            risk_score
            > cls._config_float(
                "MAX_ACCEPTABLE_RISK_SCORE",
                0.60,
            )
        ):
            reasons.append(
                "combined risk score exceeds maximum allowed level"
            )

        return reasons

    @classmethod
    def _signal_strength(
        cls,
        *,
        action: str,
        confidence: float,
        risk_score: float,
    ) -> str:
        if action == "WAIT":
            return "NONE"

        strong_threshold = cls._config_float(
            "STRONG_ADVISORY_CONFIDENCE",
            0.82,
        )

        if (
            confidence >= strong_threshold
            and risk_score <= 0.30
        ):
            return "STRONG"

        if (
            confidence
            >= cls._config_float(
                "MIN_ADVISORY_CONFIDENCE",
                0.68,
            )
            and risk_score <= 0.50
        ):
            return "MODERATE"

        return "WEAK"

    @staticmethod
    def _build_reasons(
        *,
        advisory_action: str,
        decision: CalibratedDecision,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        simulation: Optional[ScenarioSimulationResult],
        risk_score: float,
        required_confidence: float,
        data_risk: float,
        market_risk: float,
        model_risk: float,
        behavioral_risk: float,
        signal_strength: str,
        block_reasons: list[str],
    ) -> list[str]:
        reasons: list[str] = [
            f"final advisory action: {advisory_action.lower()}",
            (
                f"calibrated confidence="
                f"{decision.calibrated_confidence:.2f}"
            ),
            (
                f"required confidence="
                f"{required_confidence:.2f}"
            ),
            f"combined risk score={risk_score:.2f}",
            (
                f"risk components "
                f"data={data_risk:.2f} "
                f"market={market_risk:.2f} "
                f"model={model_risk:.2f} "
                f"behavioral={behavioral_risk:.2f}"
            ),
        ]

        if advisory_action != "WAIT":
            reasons.append(
                f"signal strength={signal_strength.lower()}"
            )

        if market.readiness_state == "READY":
            reasons.append(
                "market intelligence reports READY"
            )

        if regime.caution_required:
            reasons.append(
                f"regime caution is active: "
                f"{regime.primary_regime.lower()}"
            )

        if debate.veto_active:
            reasons.append(
                "agent veto remains active"
            )

        if simulation is not None:
            reasons.append(
                f"scenario failure probability="
                f"{simulation.failure_probability:.2f}"
            )

        if block_reasons:
            reasons.extend(
                f"blocked: {reason}"
                for reason in block_reasons
            )
        else:
            reasons.append(
                "all final safety gates passed"
            )

        reasons.append(
            "recommendation is advisory only; the human user makes the final decision"
        )

        return reasons

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            number = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return float(default)

        if number != number:
            return float(default)

        if number in {
            float("inf"),
            float("-inf"),
        }:
            return float(default)

        return number

    @staticmethod
    def _safe_int(
        value: Any,
        default: int = 0,
    ) -> int:
        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return int(default)

    @staticmethod
    def _config_float(
        name: str,
        default: float,
    ) -> float:
        try:
            return float(
                getattr(
                    CONFIG,
                    name,
                    default,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            return float(default)

    @staticmethod
    def _config_int(
        name: str,
        default: int,
    ) -> int:
        try:
            return int(
                getattr(
                    CONFIG,
                    name,
                    default,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            return int(default)

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
