from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from config import CONFIG
from intelligence.market_intelligence import MarketIntelligenceSnapshot
from intelligence.regime_detector import RegimeSnapshot


@dataclass(frozen=True, slots=True)
class AgentOpinion:
    """
    Common opinion contract used by all reasoning agents.

    direction:
        BULLISH | BEARISH | WAIT

    score:
        -1.0 .. +1.0
        Negative = bearish, positive = bullish.

    confidence:
        0.0 .. 1.0

    uncertainty:
        0.0 .. 1.0

    veto:
        True means the agent believes the setup should not be used even if
        another agent is directional. The final coordinator decides whether
        that veto is accepted.
    """

    agent: str
    direction: str
    score: float
    confidence: float
    uncertainty: float
    veto: bool

    reasons: tuple[str, ...] = field(default_factory=tuple)
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "direction": self.direction,
            "score": self.score,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "veto": self.veto,
            "reasons": list(self.reasons),
            "evidence": dict(self.evidence),
        }


class TrendAgent:
    """
    Multi-timeframe trend specialist.

    Responsibilities:
    - Treat 5m as market context.
    - Treat 1m as setup structure.
    - Treat 30s as short-term trigger confirmation.
    - Detect agreement/conflict between trend, structure and momentum.
    - Refuse weak/noisy trend conditions.

    It does NOT execute orders and it does NOT create the final bot decision.
    """

    NAME = "trend_agent"

    def evaluate(
        self,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
    ) -> AgentOpinion:
        context_5m = market.context_5m
        setup_1m = market.setup_1m
        trigger_30s = market.base_30s

        context_score = self._timeframe_score(context_5m)
        setup_score = self._timeframe_score(setup_1m)
        trigger_score = self._timeframe_score(trigger_30s)

        # 5m has the largest weight because it defines context.
        raw_score = (
            0.45 * context_score
            + 0.35 * setup_score
            + 0.20 * trigger_score
        )

        regime_score = self._regime_direction_score(regime)

        score = self._clip(
            0.80 * raw_score
            + 0.20 * regime_score,
            -1.0,
            1.0,
        )

        direction_agreement = self._direction_agreement(
            context_score,
            setup_score,
            trigger_score,
        )

        trend_strength = self._clip01(
            0.45 * context_5m.trend_quality
            + 0.35 * setup_1m.trend_quality
            + 0.20 * trigger_30s.trend_quality
        )

        structure_quality = self._clip01(
            0.45 * context_5m.structure.structure_confidence
            + 0.35 * setup_1m.structure.structure_confidence
            + 0.20 * trigger_30s.structure.structure_confidence
        )

        momentum_quality = self._clip01(
            0.45 * context_5m.momentum_score
            + 0.35 * setup_1m.momentum_score
            + 0.20 * trigger_30s.momentum_score
        )

        noise_penalty = self._clip01(
            0.50 * market.noise_score
            + 0.30 * market.conflict_score
            + 0.20 * regime.noise_strength
        )

        conflict_penalty = self._clip01(
            market.conflict_score
        )

        confidence = self._clip01(
            (
                0.30 * abs(score)
                + 0.25 * direction_agreement
                + 0.20 * trend_strength
                + 0.15 * structure_quality
                + 0.10 * momentum_quality
            )
            * (1.0 - 0.65 * noise_penalty)
            * (1.0 - 0.45 * conflict_penalty)
        )

        uncertainty = self._clip01(
            1.0
            - (
                0.40 * confidence
                + 0.25 * direction_agreement
                + 0.20 * structure_quality
                + 0.15 * trend_strength
            )
        )

        direction = self._direction(
            score=score,
            confidence=confidence,
        )

        veto = self._should_veto(
            market=market,
            regime=regime,
            direction=direction,
            confidence=confidence,
            uncertainty=uncertainty,
        )

        reasons = self._build_reasons(
            market=market,
            regime=regime,
            context_score=context_score,
            setup_score=setup_score,
            trigger_score=trigger_score,
            direction=direction,
            confidence=confidence,
            direction_agreement=direction_agreement,
            veto=veto,
        )

        evidence = {
            "context_5m_score": round(context_score, 6),
            "setup_1m_score": round(setup_score, 6),
            "trigger_30s_score": round(trigger_score, 6),
            "regime_score": round(regime_score, 6),
            "multi_timeframe_bias": round(
                market.multi_timeframe_bias, 6
            ),
            "alignment_score": round(
                market.alignment_score, 6
            ),
            "conflict_score": round(
                market.conflict_score, 6
            ),
            "trend_strength": round(
                trend_strength, 6
            ),
            "structure_quality": round(
                structure_quality, 6
            ),
            "momentum_quality": round(
                momentum_quality, 6
            ),
            "noise_penalty": round(
                noise_penalty, 6
            ),
            "regime": regime.primary_regime,
        }

        return AgentOpinion(
            agent=self.NAME,
            direction=direction,
            score=float(score),
            confidence=float(confidence),
            uncertainty=float(uncertainty),
            veto=bool(veto),
            reasons=tuple(reasons),
            evidence=evidence,
        )

    @staticmethod
    def _timeframe_score(timeframe) -> float:
        structure = timeframe.structure
        technical = timeframe.technical

        structure_score = TrendAgent._clip(
            structure.trend_score,
            -1.0,
            1.0,
        )

        ema_score = TrendAgent._clip(
            technical.ema_spread_normalized,
            -1.0,
            1.0,
        )

        directional_pressure = TrendAgent._clip(
            timeframe.directional_pressure,
            -1.0,
            1.0,
        )

        momentum_direction = TrendAgent._momentum_direction(
            technical.return_1,
            technical.return_3,
            technical.return_5,
        )

        bos_bonus = 0.0
        if structure.break_of_structure == "BULLISH":
            bos_bonus = 1.0
        elif structure.break_of_structure == "BEARISH":
            bos_bonus = -1.0

        choch_adjustment = 0.0
        if structure.change_of_character == "BULLISH":
            choch_adjustment = 0.65
        elif structure.change_of_character == "BEARISH":
            choch_adjustment = -0.65

        score = (
            0.30 * structure_score
            + 0.25 * directional_pressure
            + 0.20 * ema_score
            + 0.15 * momentum_direction
            + 0.06 * bos_bonus
            + 0.04 * choch_adjustment
        )

        # Trend evidence becomes weaker in noisy candles.
        noise_multiplier = 1.0 - (
            0.40 * timeframe.noise_score
        )

        return TrendAgent._clip(
            score * noise_multiplier,
            -1.0,
            1.0,
        )

    @staticmethod
    def _momentum_direction(
        return_1: float,
        return_3: float,
        return_5: float,
    ) -> float:
        weighted = (
            0.45 * return_1
            + 0.35 * return_3
            + 0.20 * return_5
        )

        if weighted > 0:
            return 1.0
        if weighted < 0:
            return -1.0
        return 0.0

    @staticmethod
    def _regime_direction_score(
        regime: RegimeSnapshot,
    ) -> float:
        if regime.primary_regime in {
            "BULLISH_TREND",
            "BULLISH_EXPANSION",
        }:
            base = max(
                regime.trend_strength,
                regime.expansion_strength,
            )
            return TrendAgent._clip(
                base * regime.regime_confidence,
                0.0,
                1.0,
            )

        if regime.primary_regime in {
            "BEARISH_TREND",
            "BEARISH_EXPANSION",
        }:
            base = max(
                regime.trend_strength,
                regime.expansion_strength,
            )
            return -TrendAgent._clip(
                base * regime.regime_confidence,
                0.0,
                1.0,
            )

        return TrendAgent._clip(
            regime.directional_bias * 0.35,
            -1.0,
            1.0,
        )

    @staticmethod
    def _direction_agreement(
        context_score: float,
        setup_score: float,
        trigger_score: float,
    ) -> float:
        scores = (
            context_score,
            setup_score,
            trigger_score,
        )

        signs = [
            1 if score > 0.10
            else -1 if score < -0.10
            else 0
            for score in scores
        ]

        non_zero = [
            sign
            for sign in signs
            if sign != 0
        ]

        if not non_zero:
            return 0.0

        bullish = non_zero.count(1)
        bearish = non_zero.count(-1)

        dominant = max(
            bullish,
            bearish,
        ) / len(non_zero)

        magnitude_similarity = (
            1.0
            - min(
                max(scores) - min(scores),
                2.0,
            ) / 2.0
        )

        return TrendAgent._clip01(
            0.80 * dominant
            + 0.20 * magnitude_similarity
        )

    @staticmethod
    def _direction(
        score: float,
        confidence: float,
    ) -> str:
        if (
            confidence < CONFIG.AGENT_MIN_CONFIDENCE
            or abs(score) < 0.18
        ):
            return "WAIT"

        return (
            "BULLISH"
            if score > 0
            else "BEARISH"
        )

    @staticmethod
    def _should_veto(
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        direction: str,
        confidence: float,
        uncertainty: float,
    ) -> bool:
        if market.readiness_state in {
            "WARMUP",
            "BLOCKED_NOISE",
        }:
            return True

        if regime.primary_regime == "HIGH_NOISE":
            return True

        if market.conflict_score >= 0.70:
            return True

        if regime.noise_strength >= CONFIG.HIGH_NOISE_BLOCK_THRESHOLD:
            return True

        if uncertainty >= 0.75:
            return True

        if (
            direction == "WAIT"
            and confidence < 0.35
        ):
            return True

        return False

    @staticmethod
    def _build_reasons(
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        context_score: float,
        setup_score: float,
        trigger_score: float,
        direction: str,
        confidence: float,
        direction_agreement: float,
        veto: bool,
    ) -> list[str]:
        reasons: list[str] = []

        if context_score >= 0.20:
            reasons.append("5m context supports bullish trend")
        elif context_score <= -0.20:
            reasons.append("5m context supports bearish trend")
        else:
            reasons.append("5m context is weak or neutral")

        if setup_score >= 0.20:
            reasons.append("1m setup supports bullish continuation")
        elif setup_score <= -0.20:
            reasons.append("1m setup supports bearish continuation")
        else:
            reasons.append("1m setup lacks clear trend structure")

        if trigger_score >= 0.20:
            reasons.append("30s trigger is bullish")
        elif trigger_score <= -0.20:
            reasons.append("30s trigger is bearish")
        else:
            reasons.append("30s trigger is not yet directional")

        if direction_agreement >= 0.75:
            reasons.append("timeframes show strong directional agreement")
        elif market.conflict_score >= 0.45:
            reasons.append("timeframe conflict reduces trend reliability")

        if regime.primary_regime in {
            "BULLISH_TREND",
            "BEARISH_TREND",
            "BULLISH_EXPANSION",
            "BEARISH_EXPANSION",
        }:
            reasons.append(
                f"regime supports directional analysis: "
                f"{regime.primary_regime.lower()}"
            )
        elif regime.primary_regime in {
            "RANGE",
            "COMPRESSION",
            "TRANSITION",
        }:
            reasons.append(
                f"regime is not a clean trend: "
                f"{regime.primary_regime.lower()}"
            )

        if direction == "WAIT":
            reasons.append(
                f"trend evidence is insufficient "
                f"(confidence={confidence:.2f})"
            )

        if veto:
            reasons.append(
                "trend agent requests a safety veto"
            )

        return reasons

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
