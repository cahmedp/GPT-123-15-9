from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

from agents.analyst_coordinator import AgentDebateSnapshot
from config import CONFIG
from intelligence.market_intelligence import MarketIntelligenceSnapshot
from intelligence.regime_detector import RegimeSnapshot
from memory.memory_manager import MemoryManager, SimilarMemory


@dataclass(frozen=True, slots=True)
class WorldState:
    """
    Compact state representation used by the simulation layer.

    Values are normalized so the next ScenarioEngine can compare alternative
    futures consistently.
    """

    timestamp: float
    asset: str
    price: float

    directional_bias: float       # -1 bearish .. +1 bullish
    directional_strength: float   # 0..1

    trend_strength: float         # 0..1
    compression: float            # 0..1
    expansion: float              # 0..1
    noise: float                  # 0..1
    conflict: float               # 0..1
    uncertainty: float            # 0..1
    market_quality: float         # 0..1

    bullish_memory_support: float
    bearish_memory_support: float
    wait_memory_support: float
    memory_confidence: float

    regime: str
    readiness: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "price": self.price,
            "directional_bias": self.directional_bias,
            "directional_strength": self.directional_strength,
            "trend_strength": self.trend_strength,
            "compression": self.compression,
            "expansion": self.expansion,
            "noise": self.noise,
            "conflict": self.conflict,
            "uncertainty": self.uncertainty,
            "market_quality": self.market_quality,
            "bullish_memory_support": self.bullish_memory_support,
            "bearish_memory_support": self.bearish_memory_support,
            "wait_memory_support": self.wait_memory_support,
            "memory_confidence": self.memory_confidence,
            "regime": self.regime,
            "readiness": self.readiness,
        }


@dataclass(frozen=True, slots=True)
class WorldModelSnapshot:
    """
    Output consumed by ScenarioEngine.

    The values below are scenario priors / model beliefs, not guaranteed
    real-world probabilities.
    """

    state: WorldState

    continuation_prior: float
    reversal_prior: float
    range_prior: float
    expansion_prior: float
    failure_prior: float

    memory_cases_used: int
    similar_cases: tuple[SimilarMemory, ...] = field(default_factory=tuple)

    evidence_quality: float = 0.0
    simulation_allowed: bool = False

    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.as_dict(),
            "continuation_prior": self.continuation_prior,
            "reversal_prior": self.reversal_prior,
            "range_prior": self.range_prior,
            "expansion_prior": self.expansion_prior,
            "failure_prior": self.failure_prior,
            "memory_cases_used": self.memory_cases_used,
            "similar_cases": [
                item.as_dict()
                for item in self.similar_cases
            ],
            "evidence_quality": self.evidence_quality,
            "simulation_allowed": self.simulation_allowed,
            "reasons": list(self.reasons),
        }


class WorldModel:
    """
    Builds a compact model of the current market world.

    Inputs:
        - Market Intelligence
        - Regime
        - Multi-Agent debate
        - Historical memory

    Outputs:
        - current normalized world state
        - historical-context support
        - priors for continuation / reversal / range / expansion / failure

    Important:
        - The priors are model estimates, not guaranteed probabilities.
        - No future data is read.
        - No trading orders are sent.
        - The next ScenarioEngine will use this snapshot to simulate possible
          short-horizon futures.
    """

    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
    ) -> None:
        self.memory = memory or MemoryManager()

    def build(
        self,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        memory_feature_vector: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> WorldModelSnapshot:

        if not CONFIG.WORLD_MODEL_ENABLED:
            state = self._build_state(
                market=market,
                regime=regime,
                debate=debate,
                memory_summary=None,
            )

            return WorldModelSnapshot(
                state=state,
                continuation_prior=0.0,
                reversal_prior=0.0,
                range_prior=0.0,
                expansion_prior=0.0,
                failure_prior=1.0,
                memory_cases_used=0,
                evidence_quality=0.0,
                simulation_allowed=False,
                reasons=("world model is disabled",),
            )

        feature_vector = (
            self._clean_feature_vector(
                memory_feature_vector
            )
            if memory_feature_vector is not None
            else self._default_feature_vector(
                market=market,
                regime=regime,
                debate=debate,
            )
        )

        similar_cases = self.memory.find_similar(
            feature_vector=feature_vector,
            asset=market.asset,
            timeframe_seconds=CONFIG.BASE_TIMEFRAME_SECONDS,
            resolved_only=True,
            limit=CONFIG.MEMORY_MAX_SIMILAR_CASES,
            min_similarity=0.45,
            reference_time=market.timestamp,
        )

        memory_summary = self.memory.summarize_similar(
            similar_cases
        )

        state = self._build_state(
            market=market,
            regime=regime,
            debate=debate,
            memory_summary=memory_summary,
        )

        continuation = self._continuation_prior(
            state=state,
            regime=regime,
            debate=debate,
            memory_summary=memory_summary,
        )

        reversal = self._reversal_prior(
            state=state,
            market=market,
            regime=regime,
            memory_summary=memory_summary,
        )

        range_prior = self._range_prior(
            state=state,
            regime=regime,
        )

        expansion = self._expansion_prior(
            state=state,
            market=market,
            regime=regime,
        )

        failure = self._failure_prior(
            state=state,
            debate=debate,
            memory_summary=memory_summary,
        )

        (
            continuation,
            reversal,
            range_prior,
            expansion,
            failure,
        ) = self._normalize_priors(
            continuation,
            reversal,
            range_prior,
            expansion,
            failure,
        )

        evidence_quality = self._evidence_quality(
            market=market,
            regime=regime,
            debate=debate,
            memory_summary=memory_summary,
            memory_count=len(similar_cases),
        )

        simulation_allowed = self._simulation_allowed(
            market=market,
            debate=debate,
            evidence_quality=evidence_quality,
        )

        reasons = self._build_reasons(
            state=state,
            regime=regime,
            debate=debate,
            memory_summary=memory_summary,
            memory_count=len(similar_cases),
            continuation=continuation,
            reversal=reversal,
            range_prior=range_prior,
            expansion=expansion,
            failure=failure,
            evidence_quality=evidence_quality,
            simulation_allowed=simulation_allowed,
        )

        return WorldModelSnapshot(
            state=state,
            continuation_prior=float(continuation),
            reversal_prior=float(reversal),
            range_prior=float(range_prior),
            expansion_prior=float(expansion),
            failure_prior=float(failure),
            memory_cases_used=len(similar_cases),
            similar_cases=tuple(
                similar_cases[:25]
            ),
            evidence_quality=float(evidence_quality),
            simulation_allowed=simulation_allowed,
            reasons=tuple(reasons),
        )

    def _build_state(
        self,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        memory_summary: Optional[
            Mapping[str, Any]
        ],
    ) -> WorldState:

        memory_summary = memory_summary or {}

        bullish_memory = self._clip01(
            memory_summary.get(
                "bullish_support",
                0.0,
            )
        )

        bearish_memory = self._clip01(
            memory_summary.get(
                "bearish_support",
                0.0,
            )
        )

        wait_memory = self._clip01(
            memory_summary.get(
                "wait_support",
                0.0,
            )
        )

        memory_confidence = self._clip01(
            memory_summary.get(
                "memory_confidence",
                0.0,
            )
        )

        memory_bias = (
            bullish_memory
            - bearish_memory
        )

        directional_bias = self._clip(
            (
                0.45
                * market.multi_timeframe_bias
                + 0.35
                * debate.weighted_score
                + 0.15
                * regime.directional_bias
                + 0.05
                * memory_bias
                * memory_confidence
            ),
            -1.0,
            1.0,
        )

        directional_strength = self._clip01(
            0.35
            * market.directional_conviction
            + 0.30
            * abs(
                debate.weighted_score
            )
            + 0.20
            * regime.trend_strength
            + 0.15
            * debate.consensus_confidence
        )

        return WorldState(
            timestamp=float(
                market.timestamp
            ),
            asset=market.asset,
            price=float(
                market.price
            ),

            directional_bias=float(
                directional_bias
            ),
            directional_strength=float(
                directional_strength
            ),

            trend_strength=float(
                regime.trend_strength
            ),
            compression=float(
                max(
                    market.compression_pressure,
                    regime.compression_strength,
                )
            ),
            expansion=float(
                max(
                    market.expansion_potential,
                    regime.expansion_strength,
                )
            ),
            noise=float(
                max(
                    market.noise_score,
                    regime.noise_strength,
                )
            ),
            conflict=float(
                max(
                    market.conflict_score,
                    debate.disagreement_score,
                )
            ),
            uncertainty=float(
                debate.uncertainty_score
            ),
            market_quality=float(
                market.market_quality
            ),

            bullish_memory_support=float(
                bullish_memory
            ),
            bearish_memory_support=float(
                bearish_memory
            ),
            wait_memory_support=float(
                wait_memory
            ),
            memory_confidence=float(
                memory_confidence
            ),

            regime=regime.primary_regime,
            readiness=market.readiness_state,
        )

    @classmethod
    def _continuation_prior(
        cls,
        *,
        state: WorldState,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        memory_summary: Mapping[str, Any],
    ) -> float:
        memory_support = (
            state.bullish_memory_support
            if state.directional_bias > 0
            else state.bearish_memory_support
        )

        trend_regime = (
            1.0
            if regime.primary_regime
            in {
                "BULLISH_TREND",
                "BEARISH_TREND",
                "BULLISH_EXPANSION",
                "BEARISH_EXPANSION",
            }
            else 0.25
        )

        return cls._clip01(
            0.30
            * state.directional_strength
            + 0.25
            * state.trend_strength
            + 0.20
            * debate.consensus_confidence
            + 0.15
            * trend_regime
            + 0.10
            * (
                memory_support
                * state.memory_confidence
            )
        )

    @classmethod
    def _reversal_prior(
        cls,
        *,
        state: WorldState,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        memory_summary: Mapping[str, Any],
    ) -> float:
        choch_count = sum(
            1
            for timeframe
            in (
                market.base_30s,
                market.setup_1m,
                market.context_5m,
            )
            if timeframe.structure.change_of_character
            != "NONE"
        )

        choch_score = (
            choch_count
            / 3.0
        )

        rejection = market.rejection_pressure

        transition = (
            regime.transition_strength
        )

        opposing_memory = (
            state.bearish_memory_support
            if state.directional_bias > 0
            else state.bullish_memory_support
        )

        return cls._clip01(
            0.30 * rejection
            + 0.25 * transition
            + 0.20 * choch_score
            + 0.15 * state.conflict
            + 0.10
            * opposing_memory
            * state.memory_confidence
        )

    @classmethod
    def _range_prior(
        cls,
        *,
        state: WorldState,
        regime: RegimeSnapshot,
    ) -> float:
        weak_direction = (
            1.0
            - state.directional_strength
        )

        return cls._clip01(
            0.45
            * regime.range_strength
            + 0.25
            * weak_direction
            + 0.20
            * state.compression
            + 0.10
            * state.wait_memory_support
        )

    @classmethod
    def _expansion_prior(
        cls,
        *,
        state: WorldState,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
    ) -> float:
        directional_alignment = (
            market.alignment_score
        )

        compression_release = (
            state.compression
            * max(
                state.directional_strength,
                0.25,
            )
        )

        return cls._clip01(
            0.40
            * state.expansion
            + 0.25
            * compression_release
            + 0.20
            * directional_alignment
            + 0.15
            * regime.regime_confidence
        )

    @classmethod
    def _failure_prior(
        cls,
        *,
        state: WorldState,
        debate: AgentDebateSnapshot,
        memory_summary: Mapping[str, Any],
    ) -> float:
        memory_confidence = state.memory_confidence

        memory_failure = (
            1.0
            - cls._clip01(
                memory_summary.get(
                    "positive_outcome_rate",
                    0.50,
                )
                if memory_summary.get(
                    "positive_outcome_rate"
                ) is not None
                else 0.50
            )
        )

        return cls._clip01(
            0.30
            * state.noise
            + 0.25
            * state.conflict
            + 0.20
            * state.uncertainty
            + 0.15
            * (
                1.0
                - state.market_quality
            )
            + 0.10
            * memory_failure
            * memory_confidence
        )

    @classmethod
    def _evidence_quality(
        cls,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        memory_summary: Mapping[str, Any],
        memory_count: int,
    ) -> float:

        memory_count_score = cls._clip01(
            memory_count
            / max(
                CONFIG.MIN_SIMILAR_CASES_FOR_STRONG_MEMORY,
                1,
            )
        )

        memory_quality = cls._clip01(
            memory_summary.get(
                "memory_confidence",
                0.0,
            )
        )

        return cls._clip01(
            0.25
            * market.market_quality
            + 0.20
            * regime.regime_confidence
            + 0.20
            * debate.consensus_confidence
            + 0.15
            * (
                1.0
                - debate.disagreement_score
            )
            + 0.10
            * memory_count_score
            + 0.10
            * memory_quality
        )

    @staticmethod
    def _simulation_allowed(
        *,
        market: MarketIntelligenceSnapshot,
        debate: AgentDebateSnapshot,
        evidence_quality: float,
    ) -> bool:

        if market.readiness_state in {
            "WARMUP",
            "BLOCKED_NOISE",
        }:
            return False

        if debate.veto_active:
            return False

        if (
            evidence_quality
            < 0.35
        ):
            return False

        return True

    @staticmethod
    def _normalize_priors(
        continuation: float,
        reversal: float,
        range_prior: float,
        expansion: float,
        failure: float,
    ) -> tuple[
        float,
        float,
        float,
        float,
        float,
    ]:
        values = [
            max(
                float(
                    continuation
                ),
                0.0,
            ),
            max(
                float(
                    reversal
                ),
                0.0,
            ),
            max(
                float(
                    range_prior
                ),
                0.0,
            ),
            max(
                float(
                    expansion
                ),
                0.0,
            ),
            max(
                float(
                    failure
                ),
                0.0,
            ),
        ]

        total = sum(
            values
        )

        if total <= 1e-12:
            return (
                0.20,
                0.20,
                0.20,
                0.20,
                0.20,
            )

        normalized = [
            value / total
            for value in values
        ]

        return tuple(
            float(value)
            for value in normalized
        )

    @classmethod
    def _default_feature_vector(
        cls,
        *,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
    ) -> dict[str, float]:
        return {
            "market.multi_timeframe_bias": float(
                market.multi_timeframe_bias
            ),
            "market.alignment_score": float(
                market.alignment_score
            ),
            "market.conflict_score": float(
                market.conflict_score
            ),
            "market.directional_conviction": float(
                market.directional_conviction
            ),
            "market.compression_pressure": float(
                market.compression_pressure
            ),
            "market.expansion_potential": float(
                market.expansion_potential
            ),
            "market.rejection_pressure": float(
                market.rejection_pressure
            ),
            "market.noise_score": float(
                market.noise_score
            ),
            "market.market_quality": float(
                market.market_quality
            ),

            "regime.directional_bias": float(
                regime.directional_bias
            ),
            "regime.regime_confidence": float(
                regime.regime_confidence
            ),
            "regime.trend_strength": float(
                regime.trend_strength
            ),
            "regime.compression_strength": float(
                regime.compression_strength
            ),
            "regime.expansion_strength": float(
                regime.expansion_strength
            ),
            "regime.range_strength": float(
                regime.range_strength
            ),
            "regime.noise_strength": float(
                regime.noise_strength
            ),
            "regime.transition_strength": float(
                regime.transition_strength
            ),

            "debate.weighted_score": float(
                debate.weighted_score
            ),
            "debate.consensus_confidence": float(
                debate.consensus_confidence
            ),
            "debate.disagreement_score": float(
                debate.disagreement_score
            ),
            "debate.uncertainty_score": float(
                debate.uncertainty_score
            ),
            "debate.bullish_weight": float(
                debate.bullish_weight
            ),
            "debate.bearish_weight": float(
                debate.bearish_weight
            ),
            "debate.wait_weight": float(
                debate.wait_weight
            ),
        }

    @staticmethod
    def _clean_feature_vector(
        vector: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, float]:
        result: dict[
            str,
            float
        ] = {}

        for key, value in vector.items():
            try:
                number = float(
                    value
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            if number != number:
                continue

            if number in (
                float("inf"),
                float("-inf"),
            ):
                continue

            result[
                str(key)
            ] = number

        return result

    @staticmethod
    def _build_reasons(
        *,
        state: WorldState,
        regime: RegimeSnapshot,
        debate: AgentDebateSnapshot,
        memory_summary: Mapping[str, Any],
        memory_count: int,
        continuation: float,
        reversal: float,
        range_prior: float,
        expansion: float,
        failure: float,
        evidence_quality: float,
        simulation_allowed: bool,
    ) -> list[str]:

        reasons: list[str] = []

        if state.directional_bias >= 0.20:
            reasons.append(
                "world state leans bullish"
            )
        elif state.directional_bias <= -0.20:
            reasons.append(
                "world state leans bearish"
            )
        else:
            reasons.append(
                "world state has weak directional bias"
            )

        if state.compression >= 0.65:
            reasons.append(
                "compression is materially present"
            )

        if state.expansion >= 0.65:
            reasons.append(
                "expansion pressure is elevated"
            )

        if state.noise >= 0.65:
            reasons.append(
                "noise materially reduces scenario reliability"
            )

        if state.conflict >= 0.55:
            reasons.append(
                "evidence conflict is elevated"
            )

        if memory_count > 0:
            reasons.append(
                f"{memory_count} similar historical cases were available"
            )
        else:
            reasons.append(
                "no sufficiently similar resolved historical cases were found"
            )

        memory_confidence = memory_summary.get(
            "memory_confidence",
            0.0,
        )

        if memory_confidence >= 0.60:
            reasons.append(
                "historical memory has meaningful confidence"
            )

        dominant_name, dominant_value = max(
            (
                ("continuation", continuation),
                ("reversal", reversal),
                ("range", range_prior),
                ("expansion", expansion),
                ("failure", failure),
            ),
            key=lambda item: item[1],
        )

        reasons.append(
            f"largest world-model prior: "
            f"{dominant_name} ({dominant_value:.2f})"
        )

        reasons.append(
            f"evidence quality={evidence_quality:.2f}"
        )

        if debate.veto_active:
            reasons.append(
                "agent veto is active"
            )

        if regime.caution_required:
            reasons.append(
                "regime detector requires caution"
            )

        if simulation_allowed:
            reasons.append(
                "world state is suitable for scenario simulation"
            )
        else:
            reasons.append(
                "scenario simulation is restricted until evidence improves"
            )

        return reasons

    @staticmethod
    def _clip01(
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

        return min(
            max(
                number,
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
