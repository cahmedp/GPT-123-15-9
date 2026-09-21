from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from agents.liquidity_agent import LiquidityAgent
from agents.pattern_agent import PatternAgent
from agents.risk_agent import RiskAgent
from agents.trend_agent import AgentOpinion, TrendAgent
from config import CONFIG
from intelligence.market_intelligence import MarketIntelligenceSnapshot
from intelligence.pattern_engine import PatternSnapshot
from intelligence.regime_detector import RegimeSnapshot


@dataclass(frozen=True, slots=True)
class AgentDebateSnapshot:
    """
    Result of the multi-agent debate.

    This is NOT the final trading recommendation.
    The later Decision Fusion layer combines this debate with memory,
    simulation, calibrated confidence and final risk policy.
    """

    timestamp: float
    asset: str
    price: float

    opinions: tuple[AgentOpinion, ...]

    weighted_score: float
    consensus_direction: str       # BULLISH | BEARISH | WAIT
    consensus_confidence: float    # 0..1
    disagreement_score: float      # 0..1
    uncertainty_score: float       # 0..1

    bullish_weight: float
    bearish_weight: float
    wait_weight: float

    veto_active: bool
    veto_agents: tuple[str, ...]

    ready_for_fusion: bool

    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "price": self.price,
            "opinions": [
                opinion.as_dict()
                for opinion in self.opinions
            ],
            "weighted_score": self.weighted_score,
            "consensus_direction": self.consensus_direction,
            "consensus_confidence": self.consensus_confidence,
            "disagreement_score": self.disagreement_score,
            "uncertainty_score": self.uncertainty_score,
            "bullish_weight": self.bullish_weight,
            "bearish_weight": self.bearish_weight,
            "wait_weight": self.wait_weight,
            "veto_active": self.veto_active,
            "veto_agents": list(self.veto_agents),
            "ready_for_fusion": self.ready_for_fusion,
            "reasons": list(self.reasons),
        }


class AnalystCoordinator:
    """
    Runs and coordinates the specialist reasoning agents.

    Current specialist team:
        - TrendAgent
        - LiquidityAgent
        - PatternAgent
        - RiskAgent

    Responsibilities:
        - Run each specialist on the same market snapshot.
        - Apply stable configured agent weights.
        - Measure agreement/disagreement.
        - Respect safety vetoes.
        - Produce a debate result for Decision Fusion.

    It intentionally does NOT output BUY/SELL execution commands.
    """

    def __init__(
        self,
        trend_agent: Optional[TrendAgent] = None,
        liquidity_agent: Optional[LiquidityAgent] = None,
        pattern_agent: Optional[PatternAgent] = None,
        risk_agent: Optional[RiskAgent] = None,
    ) -> None:
        self.trend_agent = trend_agent or TrendAgent()
        self.liquidity_agent = liquidity_agent or LiquidityAgent()
        self.pattern_agent = pattern_agent or PatternAgent()
        self.risk_agent = risk_agent or RiskAgent()

        self._weights = {
            TrendAgent.NAME: float(
                CONFIG.TREND_AGENT_WEIGHT
            ),
            LiquidityAgent.NAME: float(
                CONFIG.LIQUIDITY_AGENT_WEIGHT
            ),
            PatternAgent.NAME: float(
                CONFIG.PATTERN_AGENT_WEIGHT
            ),
            RiskAgent.NAME: float(
                CONFIG.RISK_AGENT_WEIGHT
            ),
        }

        self._validate_weights()

    def evaluate(
        self,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        patterns_by_timeframe: Mapping[
            int,
            PatternSnapshot,
        ],
        session_context: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> AgentDebateSnapshot:
        session_context = session_context or {}

        trend_opinion = self.trend_agent.evaluate(
            market=market,
            regime=regime,
        )

        liquidity_opinion = (
            self.liquidity_agent.evaluate(
                market=market,
                regime=regime,
                patterns_by_timeframe=patterns_by_timeframe,
            )
        )

        pattern_opinion = (
            self.pattern_agent.evaluate(
                market=market,
                regime=regime,
                patterns_by_timeframe=patterns_by_timeframe,
            )
        )

        risk_opinion = self.risk_agent.evaluate(
            market=market,
            regime=regime,
            patterns_by_timeframe=patterns_by_timeframe,
            session_context=session_context,
        )

        opinions = (
            trend_opinion,
            liquidity_opinion,
            pattern_opinion,
            risk_opinion,
        )

        weighted_score = self._weighted_score(
            opinions
        )

        bullish_weight, bearish_weight, wait_weight = (
            self._directional_weights(
                opinions
            )
        )

        disagreement = self._disagreement_score(
            opinions=opinions,
            bullish_weight=bullish_weight,
            bearish_weight=bearish_weight,
        )

        uncertainty = self._uncertainty_score(
            opinions=opinions,
            disagreement=disagreement,
        )

        veto_agents = tuple(
            opinion.agent
            for opinion in opinions
            if opinion.veto
        )

        veto_active = len(veto_agents) > 0

        consensus_direction = self._consensus_direction(
            weighted_score=weighted_score,
            bullish_weight=bullish_weight,
            bearish_weight=bearish_weight,
            wait_weight=wait_weight,
            disagreement=disagreement,
            veto_active=veto_active,
        )

        consensus_confidence = self._consensus_confidence(
            opinions=opinions,
            weighted_score=weighted_score,
            disagreement=disagreement,
            uncertainty=uncertainty,
            veto_active=veto_active,
        )

        ready_for_fusion = self._ready_for_fusion(
            market=market,
            consensus_direction=consensus_direction,
            consensus_confidence=consensus_confidence,
            disagreement=disagreement,
            uncertainty=uncertainty,
            veto_active=veto_active,
        )

        reasons = self._build_reasons(
            opinions=opinions,
            consensus_direction=consensus_direction,
            consensus_confidence=consensus_confidence,
            weighted_score=weighted_score,
            disagreement=disagreement,
            uncertainty=uncertainty,
            bullish_weight=bullish_weight,
            bearish_weight=bearish_weight,
            wait_weight=wait_weight,
            veto_agents=veto_agents,
            ready_for_fusion=ready_for_fusion,
        )

        return AgentDebateSnapshot(
            timestamp=float(market.timestamp),
            asset=market.asset,
            price=float(market.price),

            opinions=opinions,

            weighted_score=float(
                self._clip(
                    weighted_score,
                    -1.0,
                    1.0,
                )
            ),
            consensus_direction=consensus_direction,
            consensus_confidence=float(
                consensus_confidence
            ),
            disagreement_score=float(
                disagreement
            ),
            uncertainty_score=float(
                uncertainty
            ),

            bullish_weight=float(
                bullish_weight
            ),
            bearish_weight=float(
                bearish_weight
            ),
            wait_weight=float(
                wait_weight
            ),

            veto_active=veto_active,
            veto_agents=veto_agents,

            ready_for_fusion=ready_for_fusion,

            reasons=tuple(reasons),
        )

    def _weighted_score(
        self,
        opinions: tuple[AgentOpinion, ...],
    ) -> float:
        numerator = 0.0
        denominator = 0.0

        for opinion in opinions:
            base_weight = self._weights.get(
                opinion.agent,
                0.0,
            )

            if base_weight <= 0:
                continue

            # Confidence increases voting influence.
            # Uncertainty reduces it.
            effective_weight = (
                base_weight
                * max(
                    opinion.confidence,
                    0.10,
                )
                * (
                    1.0
                    - 0.65
                    * opinion.uncertainty
                )
            )

            effective_weight = max(
                effective_weight,
                0.0,
            )

            numerator += (
                opinion.score
                * effective_weight
            )
            denominator += effective_weight

        if denominator <= 1e-12:
            return 0.0

        return self._clip(
            numerator / denominator,
            -1.0,
            1.0,
        )

    def _directional_weights(
        self,
        opinions: tuple[AgentOpinion, ...],
    ) -> tuple[float, float, float]:
        bullish = 0.0
        bearish = 0.0
        wait = 0.0

        total = 0.0

        for opinion in opinions:
            base_weight = self._weights.get(
                opinion.agent,
                0.0,
            )

            if base_weight <= 0:
                continue

            confidence_weight = (
                base_weight
                * (
                    0.35
                    + 0.65
                    * opinion.confidence
                )
            )

            total += confidence_weight

            if opinion.direction == "BULLISH":
                bullish += confidence_weight

            elif opinion.direction == "BEARISH":
                bearish += confidence_weight

            else:
                wait += confidence_weight

        if total <= 1e-12:
            return 0.0, 0.0, 1.0

        return (
            self._clip01(
                bullish / total
            ),
            self._clip01(
                bearish / total
            ),
            self._clip01(
                wait / total
            ),
        )

    @classmethod
    def _disagreement_score(
        cls,
        opinions: tuple[AgentOpinion, ...],
        bullish_weight: float,
        bearish_weight: float,
    ) -> float:
        directional_total = (
            bullish_weight
            + bearish_weight
        )

        if directional_total > 1e-12:
            direction_conflict = (
                2.0
                * min(
                    bullish_weight,
                    bearish_weight,
                )
                / directional_total
            )
        else:
            direction_conflict = 0.0

        scores = [
            opinion.score
            for opinion in opinions
        ]

        if scores:
            score_span = min(
                max(scores) - min(scores),
                2.0,
            ) / 2.0
        else:
            score_span = 0.0

        explicit_wait = (
            sum(
                1
                for opinion in opinions
                if opinion.direction == "WAIT"
            )
            / max(
                len(opinions),
                1,
            )
        )

        return cls._clip01(
            0.55 * direction_conflict
            + 0.30 * score_span
            + 0.15 * explicit_wait
        )

    @classmethod
    def _uncertainty_score(
        cls,
        opinions: tuple[AgentOpinion, ...],
        disagreement: float,
    ) -> float:
        if not opinions:
            return 1.0

        average_uncertainty = sum(
            opinion.uncertainty
            for opinion in opinions
        ) / len(opinions)

        low_confidence = (
            1.0
            - (
                sum(
                    opinion.confidence
                    for opinion in opinions
                )
                / len(opinions)
            )
        )

        return cls._clip01(
            0.50 * average_uncertainty
            + 0.30 * disagreement
            + 0.20 * low_confidence
        )

    @classmethod
    def _consensus_direction(
        cls,
        weighted_score: float,
        bullish_weight: float,
        bearish_weight: float,
        wait_weight: float,
        disagreement: float,
        veto_active: bool,
    ) -> str:
        if veto_active:
            return "WAIT"

        if disagreement >= 0.70:
            return "WAIT"

        if wait_weight >= 0.50:
            return "WAIT"

        if abs(weighted_score) < 0.16:
            return "WAIT"

        if (
            weighted_score > 0
            and bullish_weight
            > bearish_weight
        ):
            return "BULLISH"

        if (
            weighted_score < 0
            and bearish_weight
            > bullish_weight
        ):
            return "BEARISH"

        return "WAIT"

    @classmethod
    def _consensus_confidence(
        cls,
        opinions: tuple[AgentOpinion, ...],
        weighted_score: float,
        disagreement: float,
        uncertainty: float,
        veto_active: bool,
    ) -> float:
        if not opinions:
            return 0.0

        weighted_confidence = 0.0
        total_weight = 0.0

        config_weights = {
            TrendAgent.NAME: float(
                CONFIG.TREND_AGENT_WEIGHT
            ),
            LiquidityAgent.NAME: float(
                CONFIG.LIQUIDITY_AGENT_WEIGHT
            ),
            PatternAgent.NAME: float(
                CONFIG.PATTERN_AGENT_WEIGHT
            ),
            RiskAgent.NAME: float(
                CONFIG.RISK_AGENT_WEIGHT
            ),
        }

        for opinion in opinions:
            weight = config_weights.get(
                opinion.agent,
                0.0,
            )

            weighted_confidence += (
                opinion.confidence
                * weight
            )
            total_weight += weight

        base_confidence = (
            weighted_confidence / total_weight
            if total_weight > 1e-12
            else 0.0
        )

        score_strength = abs(
            weighted_score
        )

        confidence = (
            0.55 * base_confidence
            + 0.25 * score_strength
            + 0.20 * (
                1.0 - uncertainty
            )
        )

        confidence *= (
            1.0
            - 0.70 * disagreement
        )

        if veto_active:
            confidence *= 0.35

        return cls._clip01(
            confidence
        )

    @staticmethod
    def _ready_for_fusion(
        market: MarketIntelligenceSnapshot,
        consensus_direction: str,
        consensus_confidence: float,
        disagreement: float,
        uncertainty: float,
        veto_active: bool,
    ) -> bool:
        if veto_active:
            return False

        if market.readiness_state in {
            "WARMUP",
            "BLOCKED_NOISE",
        }:
            return False

        if consensus_direction == "WAIT":
            return False

        if (
            consensus_confidence
            < CONFIG.AGENT_MIN_CONFIDENCE
        ):
            return False

        if (
            disagreement
            > CONFIG.AGENT_CONFLICT_THRESHOLD
        ):
            return False

        if (
            uncertainty
            > CONFIG.MAX_UNCERTAINTY_FOR_DIRECTIONAL_ADVICE
        ):
            return False

        return True

    @staticmethod
    def _build_reasons(
        opinions: tuple[AgentOpinion, ...],
        consensus_direction: str,
        consensus_confidence: float,
        weighted_score: float,
        disagreement: float,
        uncertainty: float,
        bullish_weight: float,
        bearish_weight: float,
        wait_weight: float,
        veto_agents: tuple[str, ...],
        ready_for_fusion: bool,
    ) -> list[str]:
        reasons: list[str] = []

        directional_agents = [
            opinion
            for opinion in opinions
            if opinion.direction
            in {
                "BULLISH",
                "BEARISH",
            }
        ]

        bullish_agents = [
            opinion.agent
            for opinion in directional_agents
            if opinion.direction == "BULLISH"
        ]

        bearish_agents = [
            opinion.agent
            for opinion in directional_agents
            if opinion.direction == "BEARISH"
        ]

        if bullish_agents:
            reasons.append(
                "bullish agents: "
                + ", ".join(
                    bullish_agents
                )
            )

        if bearish_agents:
            reasons.append(
                "bearish agents: "
                + ", ".join(
                    bearish_agents
                )
            )

        reasons.append(
            f"debate consensus: "
            f"{consensus_direction.lower()}"
        )

        reasons.append(
            f"weighted score={weighted_score:.2f}"
        )

        reasons.append(
            f"confidence={consensus_confidence:.2f}"
        )

        reasons.append(
            f"disagreement={disagreement:.2f}"
        )

        reasons.append(
            f"uncertainty={uncertainty:.2f}"
        )

        reasons.append(
            f"vote weights "
            f"B={bullish_weight:.2f} "
            f"S={bearish_weight:.2f} "
            f"W={wait_weight:.2f}"
        )

        if veto_agents:
            reasons.append(
                "active veto: "
                + ", ".join(
                    veto_agents
                )
            )

        if disagreement >= 0.50:
            reasons.append(
                "agents materially disagree"
            )

        if uncertainty >= 0.50:
            reasons.append(
                "overall reasoning uncertainty is elevated"
            )

        if ready_for_fusion:
            reasons.append(
                "multi-agent debate is ready for final fusion"
            )
        else:
            reasons.append(
                "multi-agent debate requires WAIT or more confirmation"
            )

        return reasons

    def _validate_weights(self) -> None:
        if any(
            weight < 0
            for weight in self._weights.values()
        ):
            raise ValueError(
                "Agent weights cannot be negative."
            )

        if sum(
            self._weights.values()
        ) <= 0:
            raise ValueError(
                "At least one agent weight must be positive."
            )

    @staticmethod
    def _clip01(value: float) -> float:
        return min(
            max(float(value), 0.0),
            1.0,
        )

    @staticmethod
    def _clip(
        value: float,
        low: float,
        high: float,
    ) -> float:
        return min(
            max(float(value), low),
            high,
        )
