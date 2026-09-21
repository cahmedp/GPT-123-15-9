from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from agents.analyst_coordinator import AgentDebateSnapshot
from config import CONFIG
from intelligence.market_intelligence import MarketIntelligenceSnapshot
from intelligence.regime_detector import RegimeSnapshot
from simulation.scenario_engine import ScenarioSimulationResult
from simulation.world_model import WorldModelSnapshot


@dataclass(frozen=True, slots=True)
class FusionDecision:
    """
    Raw advisory decision produced before confidence calibration and the final
    independent RiskManager gate.

    action:
        BUY | SELL | WAIT

    This is advisory only. It never executes a Pocket Option order.
    """

    timestamp: float
    asset: str
    price: float

    action: str
    direction: str

    fusion_score: float
    raw_confidence: float
    uncertainty: float

    bullish_evidence: float
    bearish_evidence: float
    wait_evidence: float

    agent_component: float
    market_component: float
    regime_component: float
    world_component: float
    simulation_component: float
    memory_component: float
    knowledge_component: float

    veto_active: bool
    blocked_reason: Optional[str]

    ready_for_confidence_calibration: bool

    reasons: tuple[str, ...] = field(default_factory=tuple)
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "price": self.price,
            "action": self.action,
            "direction": self.direction,
            "fusion_score": self.fusion_score,
            "raw_confidence": self.raw_confidence,
            "uncertainty": self.uncertainty,
            "bullish_evidence": self.bullish_evidence,
            "bearish_evidence": self.bearish_evidence,
            "wait_evidence": self.wait_evidence,
            "agent_component": self.agent_component,
            "market_component": self.market_component,
            "regime_component": self.regime_component,
            "world_component": self.world_component,
            "simulation_component": self.simulation_component,
            "memory_component": self.memory_component,
            "knowledge_component": self.knowledge_component,
            "veto_active": self.veto_active,
            "blocked_reason": self.blocked_reason,
            "ready_for_confidence_calibration": (
                self.ready_for_confidence_calibration
            ),
            "reasons": list(self.reasons),
            "evidence": dict(self.evidence),
        }


class DecisionFusionEngine:
    """
    Fuses all major evidence sources into one RAW advisory opinion.

    Sources:
        1) Multi-Agent debate
        2) Market Intelligence
        3) Regime Detector
        4) World Model
        5) Scenario Simulation
        6) Similar historical memory
        7) Consolidated KnowledgeBase support

    Important:
        - This is NOT the last safety layer.
        - ConfidenceEngine calibrates raw confidence next.
        - RiskManager performs the final independent safety gate later.
        - No trade execution exists here.
    """

    def __init__(self) -> None:
        # OTC 30s execution tuning:
        # Prioritize live agents and market state over slow historical context.
        # This changes weighting only; no execution logic is introduced.
        self._weights = {
            "agents": 0.45,
            "market": 0.25,
            "regime": 0.10,
            "world": 0.05,
            "simulation": 0.10,
            "memory": 0.03,
            "knowledge": 0.02,
        }

        self._validate_weights()

    def fuse(
        self,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        world: WorldModelSnapshot,
        simulation: ScenarioSimulationResult,
        memory_summary: Optional[
            Mapping[str, Any]
        ] = None,
        knowledge_support: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> FusionDecision:
        memory_summary = memory_summary or {}
        knowledge_support = knowledge_support or {}

        agent_component = self._clip(
            debate.weighted_score,
            -1.0,
            1.0,
        )

        market_component = self._clip(
            market.multi_timeframe_bias
            * (
                0.55
                + 0.45
                * market.directional_conviction
            ),
            -1.0,
            1.0,
        )

        regime_component = self._clip(
            regime.directional_bias
            * (
                0.50
                + 0.50
                * regime.regime_confidence
            ),
            -1.0,
            1.0,
        )

        world_component = self._clip(
            world.state.directional_bias
            * (
                0.55
                + 0.45
                * world.evidence_quality
            ),
            -1.0,
            1.0,
        )

        simulation_component = self._simulation_component(
            simulation
        )

        memory_component = self._memory_component(
            memory_summary
        )

        knowledge_component = self._knowledge_component(
            knowledge_support
        )

        fusion_score = self._clip(
            self._weights["agents"]
            * agent_component
            + self._weights["market"]
            * market_component
            + self._weights["regime"]
            * regime_component
            + self._weights["world"]
            * world_component
            + self._weights["simulation"]
            * simulation_component
            + self._weights["memory"]
            * memory_component
            + self._weights["knowledge"]
            * knowledge_component,
            -1.0,
            1.0,
        )

        bullish_evidence = self._directional_evidence(
            positive=True,
            agent_component=agent_component,
            market_component=market_component,
            regime_component=regime_component,
            world_component=world_component,
            simulation_component=simulation_component,
            memory_component=memory_component,
            knowledge_component=knowledge_component,
        )

        bearish_evidence = self._directional_evidence(
            positive=False,
            agent_component=agent_component,
            market_component=market_component,
            regime_component=regime_component,
            world_component=world_component,
            simulation_component=simulation_component,
            memory_component=memory_component,
            knowledge_component=knowledge_component,
        )

        wait_evidence = self._wait_evidence(
            market=market,
            regime=regime,
            debate=debate,
            world=world,
            simulation=simulation,
            memory_summary=memory_summary,
            knowledge_support=knowledge_support,
        )

        veto_active, blocked_reason = self._hard_block(
            market=market,
            regime=regime,
            debate=debate,
            world=world,
        )

        source_agreement = self._source_agreement(
            (
                agent_component,
                market_component,
                regime_component,
                world_component,
                simulation_component,
                memory_component,
                knowledge_component,
            )
        )

        raw_confidence = self._raw_confidence(
            fusion_score=fusion_score,
            source_agreement=source_agreement,
            market=market,
            regime=regime,
            debate=debate,
            world=world,
            simulation=simulation,
            wait_evidence=wait_evidence,
        )

        uncertainty = self._uncertainty(
            market=market,
            regime=regime,
            debate=debate,
            world=world,
            simulation=simulation,
            source_agreement=source_agreement,
        )

        action = self._select_action(
            fusion_score=fusion_score,
            raw_confidence=raw_confidence,
            uncertainty=uncertainty,
            bullish_evidence=bullish_evidence,
            bearish_evidence=bearish_evidence,
            wait_evidence=wait_evidence,
            veto_active=veto_active,
        )

        direction = {
            "BUY": "BULLISH",
            "SELL": "BEARISH",
            "WAIT": "WAIT",
        }[action]

        ready_for_confidence_calibration = (
            not veto_active
            and action in {"BUY", "SELL"}
            and raw_confidence >= 0.40
            and uncertainty < 0.70
        )

        reasons = self._build_reasons(
            action=action,
            fusion_score=fusion_score,
            raw_confidence=raw_confidence,
            uncertainty=uncertainty,
            bullish_evidence=bullish_evidence,
            bearish_evidence=bearish_evidence,
            wait_evidence=wait_evidence,
            source_agreement=source_agreement,
            veto_active=veto_active,
            blocked_reason=blocked_reason,
            debate=debate,
            market=market,
            regime=regime,
            simulation=simulation,
        )

        evidence = {
            "source_agreement": round(
                source_agreement,
                6,
            ),
            "agent_consensus_direction": (
                debate.consensus_direction
            ),
            "agent_consensus_confidence": round(
                debate.consensus_confidence,
                6,
            ),
            "market_readiness": (
                market.readiness_state
            ),
            "market_quality": round(
                market.market_quality,
                6,
            ),
            "regime": (
                regime.primary_regime
            ),
            "regime_confidence": round(
                regime.regime_confidence,
                6,
            ),
            "world_evidence_quality": round(
                world.evidence_quality,
                6,
            ),
            "simulation_confidence": round(
                simulation.simulation_confidence,
                6,
            ),
            "simulation_direction": (
                simulation.dominant_direction
            ),
            "simulation_failure_probability": round(
                simulation.failure_probability,
                6,
            ),
            "memory_count": int(
                memory_summary.get(
                    "count",
                    0,
                )
                or 0
            ),
            "memory_confidence": round(
                self._safe_float(
                    memory_summary.get(
                        "memory_confidence",
                        0.0,
                    )
                ),
                6,
            ),
            "knowledge_count": int(
                knowledge_support.get(
                    "count",
                    0,
                )
                or 0
            ),
            "knowledge_confidence": round(
                self._safe_float(
                    knowledge_support.get(
                        "knowledge_confidence",
                        0.0,
                    )
                ),
                6,
            ),
        }

        return FusionDecision(
            timestamp=float(
                market.timestamp
            ),
            asset=market.asset,
            price=float(
                market.price
            ),

            action=action,
            direction=direction,

            fusion_score=float(
                fusion_score
            ),
            raw_confidence=float(
                raw_confidence
            ),
            uncertainty=float(
                uncertainty
            ),

            bullish_evidence=float(
                bullish_evidence
            ),
            bearish_evidence=float(
                bearish_evidence
            ),
            wait_evidence=float(
                wait_evidence
            ),

            agent_component=float(
                agent_component
            ),
            market_component=float(
                market_component
            ),
            regime_component=float(
                regime_component
            ),
            world_component=float(
                world_component
            ),
            simulation_component=float(
                simulation_component
            ),
            memory_component=float(
                memory_component
            ),
            knowledge_component=float(
                knowledge_component
            ),

            veto_active=veto_active,
            blocked_reason=blocked_reason,

            ready_for_confidence_calibration=(
                ready_for_confidence_calibration
            ),

            reasons=tuple(
                reasons
            ),
            evidence=evidence,
        )

    @classmethod
    def _simulation_component(
        cls,
        simulation: ScenarioSimulationResult,
    ) -> float:
        if not simulation.usable_for_fusion:
            return 0.0

        direction = cls._clip(
            simulation.expected_directional_score,
            -1.0,
            1.0,
        )

        confidence_multiplier = (
            0.40
            + 0.60
            * simulation.simulation_confidence
        )

        failure_multiplier = (
            1.0
            - 0.75
            * simulation.failure_probability
        )

        return cls._clip(
            direction
            * confidence_multiplier
            * max(
                failure_multiplier,
                0.0,
            ),
            -1.0,
            1.0,
        )

    @classmethod
    def _memory_component(
        cls,
        summary: Mapping[str, Any],
    ) -> float:
        bullish = cls._clip01(
            cls._safe_float(
                summary.get(
                    "bullish_support",
                    0.0,
                )
            )
        )

        bearish = cls._clip01(
            cls._safe_float(
                summary.get(
                    "bearish_support",
                    0.0,
                )
            )
        )

        confidence = cls._clip01(
            cls._safe_float(
                summary.get(
                    "memory_confidence",
                    0.0,
                )
            )
        )

        return cls._clip(
            (
                bullish - bearish
            )
            * confidence,
            -1.0,
            1.0,
        )

    @classmethod
    def _knowledge_component(
        cls,
        support: Mapping[str, Any],
    ) -> float:
        bullish = cls._clip01(
            cls._safe_float(
                support.get(
                    "bullish_support",
                    0.0,
                )
            )
        )

        bearish = cls._clip01(
            cls._safe_float(
                support.get(
                    "bearish_support",
                    0.0,
                )
            )
        )

        confidence = cls._clip01(
            cls._safe_float(
                support.get(
                    "knowledge_confidence",
                    0.0,
                )
            )
        )

        return cls._clip(
            (
                bullish - bearish
            )
            * confidence,
            -1.0,
            1.0,
        )

    def _directional_evidence(
        self,
        *,
        positive: bool,
        agent_component: float,
        market_component: float,
        regime_component: float,
        world_component: float,
        simulation_component: float,
        memory_component: float,
        knowledge_component: float,
    ) -> float:
        components = {
            "agents": agent_component,
            "market": market_component,
            "regime": regime_component,
            "world": world_component,
            "simulation": simulation_component,
            "memory": memory_component,
            "knowledge": knowledge_component,
        }

        evidence = 0.0

        for name, value in components.items():
            weight = self._weights[name]

            if positive:
                contribution = max(
                    value,
                    0.0,
                )
            else:
                contribution = max(
                    -value,
                    0.0,
                )

            evidence += (
                contribution
                * weight
            )

        return self._clip01(
            evidence
            / max(
                sum(
                    self._weights.values()
                ),
                1e-12,
            )
        )

    @classmethod
    def _wait_evidence(
        cls,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        world: WorldModelSnapshot,
        simulation: ScenarioSimulationResult,
        memory_summary: Mapping[str, Any],
        knowledge_support: Mapping[str, Any],
    ) -> float:
        memory_wait = cls._clip01(
            cls._safe_float(
                memory_summary.get(
                    "wait_support",
                    0.0,
                )
            )
        )

        knowledge_wait = cls._clip01(
            cls._safe_float(
                knowledge_support.get(
                    "wait_support",
                    0.0,
                )
            )
        )

        readiness_risk = {
            "READY": 0.0,
            "OBSERVE": 0.25,
            "WAIT_LOW_QUALITY": 0.65,
            "WAIT_CONFLICT": 0.80,
            "BLOCKED_NOISE": 1.0,
            "WARMUP": 1.0,
        }.get(
            market.readiness_state,
            0.50,
        )

        regime_caution = (
            0.70
            if regime.caution_required
            else 0.0
        )

        simulation_wait = max(
            simulation.sideways_probability,
            simulation.failure_probability,
        )

        return cls._clip01(
            0.25
            * debate.wait_weight
            + 0.20
            * debate.uncertainty_score
            + 0.15
            * readiness_risk
            + 0.10
            * regime_caution
            + 0.15
            * simulation_wait
            + 0.075
            * memory_wait
            + 0.075
            * knowledge_wait
        )

    @classmethod
    def _hard_block(
        cls,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        world: WorldModelSnapshot,
    ) -> tuple[bool, Optional[str]]:
        if debate.veto_active:
            return (
                True,
                "multi-agent safety veto",
            )

        if market.readiness_state == "WARMUP":
            return (
                True,
                "market intelligence is still warming up",
            )

        if market.readiness_state == "BLOCKED_NOISE":
            return (
                True,
                "market noise exceeds allowed level",
            )

        if regime.primary_regime == "HIGH_NOISE":
            return (
                True,
                "high-noise market regime",
            )

        if (
            market.conflict_score
            >= 0.80
        ):
            return (
                True,
                "extreme multi-timeframe conflict",
            )

        if (
            debate.uncertainty_score
            >= 0.85
        ):
            return (
                True,
                "extreme multi-agent uncertainty",
            )

        if (
            world.failure_prior
            >= 0.60
            and world.evidence_quality
            < 0.45
        ):
            return (
                True,
                "world model evidence is unreliable",
            )

        return (
            False,
            None,
        )

    @classmethod
    def _raw_confidence(
        cls,
        *,
        fusion_score: float,
        source_agreement: float,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        world: WorldModelSnapshot,
        simulation: ScenarioSimulationResult,
        wait_evidence: float,
    ) -> float:
        simulation_confidence = (
            simulation.simulation_confidence
            if simulation.usable_for_fusion
            else 0.0
        )

        confidence = (
            0.24
            * abs(
                fusion_score
            )
            + 0.20
            * source_agreement
            + 0.16
            * debate.consensus_confidence
            + 0.12
            * market.market_quality
            + 0.10
            * regime.regime_confidence
            + 0.08
            * world.evidence_quality
            + 0.10
            * simulation_confidence
        )

        confidence *= (
            1.0
            - 0.55
            * wait_evidence
        )

        confidence *= (
            1.0
            - 0.45
            * debate.disagreement_score
        )

        return cls._clip01(
            confidence
        )

    @classmethod
    def _uncertainty(
        cls,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        world: WorldModelSnapshot,
        simulation: ScenarioSimulationResult,
        source_agreement: float,
    ) -> float:
        simulation_uncertainty = (
            simulation.scenario_disagreement
            if simulation.usable_for_fusion
            else 0.65
        )

        return cls._clip01(
            0.28
            * debate.uncertainty_score
            + 0.22
            * debate.disagreement_score
            + 0.15
            * market.conflict_score
            + 0.10
            * regime.transition_strength
            + 0.10
            * (
                1.0
                - world.evidence_quality
            )
            + 0.10
            * simulation_uncertainty
            + 0.05
            * (
                1.0
                - source_agreement
            )
        )

    @classmethod
    def _select_action(
        cls,
        *,
        fusion_score: float,
        raw_confidence: float,
        uncertainty: float,
        bullish_evidence: float,
        bearish_evidence: float,
        wait_evidence: float,
        veto_active: bool,
    ) -> str:
        if veto_active:
            return "WAIT"

        if (
            uncertainty
            > CONFIG.MAX_UNCERTAINTY_FOR_DIRECTIONAL_ADVICE
        ):
            return "WAIT"

        if raw_confidence < 0.45:
            return "WAIT"

        if wait_evidence >= 0.55:
            return "WAIT"

        if (
            fusion_score >= 0.18
            and bullish_evidence
            > bearish_evidence
        ):
            return "BUY"

        if (
            fusion_score <= -0.18
            and bearish_evidence
            > bullish_evidence
        ):
            return "SELL"

        return "WAIT"

    @classmethod
    def _source_agreement(
        cls,
        components: tuple[float, ...],
    ) -> float:
        active = [
            value
            for value in components
            if abs(value) >= 0.05
        ]

        if not active:
            return 0.0

        bullish = sum(
            1
            for value in active
            if value > 0
        )

        bearish = sum(
            1
            for value in active
            if value < 0
        )

        dominant_count = max(
            bullish,
            bearish,
        )

        directional_agreement = (
            dominant_count
            / len(active)
        )

        magnitudes = [
            abs(value)
            for value in active
        ]

        mean_magnitude = (
            sum(magnitudes)
            / len(magnitudes)
        )

        if mean_magnitude <= 1e-12:
            magnitude_consistency = 0.0
        else:
            average_deviation = (
                sum(
                    abs(
                        value
                        - mean_magnitude
                    )
                    for value
                    in magnitudes
                )
                / len(magnitudes)
            )

            magnitude_consistency = (
                1.0
                - min(
                    average_deviation
                    / max(
                        mean_magnitude,
                        1e-12,
                    ),
                    1.0,
                )
            )

        return cls._clip01(
            0.80
            * directional_agreement
            + 0.20
            * magnitude_consistency
        )

    @staticmethod
    def _build_reasons(
        *,
        action: str,
        fusion_score: float,
        raw_confidence: float,
        uncertainty: float,
        bullish_evidence: float,
        bearish_evidence: float,
        wait_evidence: float,
        source_agreement: float,
        veto_active: bool,
        blocked_reason: Optional[str],
        debate: AgentDebateSnapshot,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        simulation: ScenarioSimulationResult,
    ) -> list[str]:
        reasons: list[str] = []

        reasons.append(
            f"raw fusion action: {action.lower()}"
        )

        if fusion_score >= 0.18:
            reasons.append(
                "combined evidence leans bullish"
            )
        elif fusion_score <= -0.18:
            reasons.append(
                "combined evidence leans bearish"
            )
        else:
            reasons.append(
                "combined directional edge is weak"
            )

        reasons.append(
            f"fusion score={fusion_score:.2f}"
        )

        reasons.append(
            f"raw confidence={raw_confidence:.2f}"
        )

        reasons.append(
            f"uncertainty={uncertainty:.2f}"
        )

        reasons.append(
            f"source agreement={source_agreement:.2f}"
        )

        reasons.append(
            f"evidence B={bullish_evidence:.2f} "
            f"S={bearish_evidence:.2f} "
            f"W={wait_evidence:.2f}"
        )

        if debate.consensus_direction != "WAIT":
            reasons.append(
                f"agents lean "
                f"{debate.consensus_direction.lower()}"
            )

        if market.readiness_state != "READY":
            reasons.append(
                f"market readiness is "
                f"{market.readiness_state.lower()}"
            )

        if regime.caution_required:
            reasons.append(
                f"regime requires caution: "
                f"{regime.primary_regime.lower()}"
            )

        if simulation.usable_for_fusion:
            reasons.append(
                f"simulation leans "
                f"{simulation.dominant_direction.lower()}"
            )
        else:
            reasons.append(
                "simulation evidence is not strong enough for material weight"
            )

        if veto_active:
            reasons.append(
                f"decision blocked: "
                f"{blocked_reason or 'safety veto'}"
            )

        if action == "WAIT":
            reasons.append(
                "final calibration/risk layers must not convert WAIT into a "
                "directional call without stronger evidence"
            )

        return reasons

    def _validate_weights(self) -> None:
        if any(
            value < 0
            for value in self._weights.values()
        ):
            raise ValueError(
                "Decision fusion weights cannot be negative."
            )

        total = sum(
            self._weights.values()
        )

        if total <= 0:
            raise ValueError(
                "Decision fusion weights must have positive total."
            )

        if abs(
            total - 1.0
        ) > 1e-9:
            raise ValueError(
                "Decision fusion weights must sum to 1.0."
            )

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float:
        try:
            number = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return 0.0

        if number != number:
            return 0.0

        if number in (
            float("inf"),
            float("-inf"),
        ):
            return 0.0

        return number

    @classmethod
    def _clip01(
        cls,
        value: Any,
    ) -> float:
        return min(
            max(
                cls._safe_float(
                    value
                ),
                0.0,
            ),
            1.0,
        )

    @staticmethod
    def _clip(
        value: float,
        low: float,
        high: float,
    ) -> float:
        return min(
            max(
                float(value),
                low,
            ),
            high,
        )
