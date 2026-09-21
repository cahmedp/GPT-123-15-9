from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional

from config import CONFIG
from intelligence.market_intelligence import (
    MarketIntelligenceSnapshot,
    TimeframeIntelligence,
)
from intelligence.pattern_engine import PatternSnapshot


@dataclass(frozen=True, slots=True)
class RegimeSnapshot:
    timestamp: float
    asset: str
    price: float

    primary_regime: str
    secondary_regime: str

    directional_bias: float          # -1 bearish .. +1 bullish
    regime_confidence: float         # 0..1

    trend_strength: float            # 0..1
    compression_strength: float      # 0..1
    expansion_strength: float        # 0..1
    range_strength: float            # 0..1
    noise_strength: float            # 0..1
    transition_strength: float       # 0..1

    volatility_state: str            # LOW | NORMAL | HIGH | EXTREME
    structure_state: str             # BULLISH | BEARISH | RANGE | TRANSITION
    alignment_state: str             # ALIGNED | PARTIAL | CONFLICTED

    suitable_for_directional_analysis: bool
    caution_required: bool

    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "price": self.price,
            "primary_regime": self.primary_regime,
            "secondary_regime": self.secondary_regime,
            "directional_bias": self.directional_bias,
            "regime_confidence": self.regime_confidence,
            "trend_strength": self.trend_strength,
            "compression_strength": self.compression_strength,
            "expansion_strength": self.expansion_strength,
            "range_strength": self.range_strength,
            "noise_strength": self.noise_strength,
            "transition_strength": self.transition_strength,
            "volatility_state": self.volatility_state,
            "structure_state": self.structure_state,
            "alignment_state": self.alignment_state,
            "suitable_for_directional_analysis": (
                self.suitable_for_directional_analysis
            ),
            "caution_required": self.caution_required,
            "reasons": self.reasons,
        }


class RegimeDetector:
    """
    Detects the current market regime from the already-built intelligence layer.

    The detector does not use future data and does not issue trade orders.

    Main regimes:
    - BULLISH_TREND
    - BEARISH_TREND
    - RANGE
    - COMPRESSION
    - BULLISH_EXPANSION
    - BEARISH_EXPANSION
    - HIGH_NOISE
    - TRANSITION

    The regime is later consumed by agents, memory, simulation and risk.
    """

    def __init__(
        self,
        trend_threshold: float = CONFIG.TREND_STRENGTH_THRESHOLD,
        high_noise_threshold: float = CONFIG.HIGH_NOISE_BLOCK_THRESHOLD,
    ) -> None:
        if not 0.0 <= trend_threshold <= 1.0:
            raise ValueError("trend_threshold must be between 0 and 1.")

        if not 0.0 <= high_noise_threshold <= 1.0:
            raise ValueError(
                "high_noise_threshold must be between 0 and 1."
            )

        self.trend_threshold = float(trend_threshold)
        self.high_noise_threshold = float(high_noise_threshold)

    def detect(
        self,
        market: MarketIntelligenceSnapshot,
        patterns_by_timeframe: Optional[
            Mapping[int, PatternSnapshot]
        ] = None,
    ) -> RegimeSnapshot:
        patterns_by_timeframe = patterns_by_timeframe or {}

        pattern_bias, pattern_conflict = self._aggregate_pattern_bias(
            patterns_by_timeframe.values()
        )

        directional_bias = self._clip(
            (
                market.multi_timeframe_bias * 0.80
                + pattern_bias * 0.20
            ),
            -1.0,
            1.0,
        )

        trend_strength = self._trend_strength(
            market=market,
            directional_bias=directional_bias,
        )

        compression_strength = self._compression_strength(
            market=market,
            patterns_by_timeframe=patterns_by_timeframe,
        )

        expansion_strength = self._expansion_strength(
            market=market,
            patterns_by_timeframe=patterns_by_timeframe,
        )

        noise_strength = self._noise_strength(
            market=market,
            pattern_conflict=pattern_conflict,
        )

        range_strength = self._range_strength(
            market=market,
            trend_strength=trend_strength,
            compression_strength=compression_strength,
            expansion_strength=expansion_strength,
        )

        transition_strength = self._transition_strength(
            market=market,
            pattern_conflict=pattern_conflict,
            trend_strength=trend_strength,
        )

        volatility_state = self._volatility_state(
            market.base_30s,
            market.setup_1m,
            market.context_5m,
        )

        structure_state = market.context_5m.structure.structure_state
        alignment_state = self._alignment_state(
            alignment=market.alignment_score,
            conflict=market.conflict_score,
        )

        primary_regime, primary_score = self._choose_primary_regime(
            directional_bias=directional_bias,
            trend_strength=trend_strength,
            compression_strength=compression_strength,
            expansion_strength=expansion_strength,
            range_strength=range_strength,
            noise_strength=noise_strength,
            transition_strength=transition_strength,
        )

        secondary_regime, secondary_score = self._choose_secondary_regime(
            primary_regime=primary_regime,
            directional_bias=directional_bias,
            trend_strength=trend_strength,
            compression_strength=compression_strength,
            expansion_strength=expansion_strength,
            range_strength=range_strength,
            noise_strength=noise_strength,
            transition_strength=transition_strength,
        )

        regime_confidence = self._regime_confidence(
            primary_score=primary_score,
            secondary_score=secondary_score,
            market=market,
            pattern_conflict=pattern_conflict,
        )

        suitable = self._suitable_for_directional_analysis(
            primary_regime=primary_regime,
            regime_confidence=regime_confidence,
            market=market,
            noise_strength=noise_strength,
        )

        caution_required = (
            noise_strength >= 0.60
            or transition_strength >= 0.60
            or market.conflict_score >= 0.45
            or regime_confidence < 0.55
        )

        reasons = self._build_reasons(
            primary_regime=primary_regime,
            secondary_regime=secondary_regime,
            directional_bias=directional_bias,
            trend_strength=trend_strength,
            compression_strength=compression_strength,
            expansion_strength=expansion_strength,
            range_strength=range_strength,
            noise_strength=noise_strength,
            transition_strength=transition_strength,
            volatility_state=volatility_state,
            alignment_state=alignment_state,
            market=market,
        )

        return RegimeSnapshot(
            timestamp=float(market.timestamp),
            asset=market.asset,
            price=float(market.price),

            primary_regime=primary_regime,
            secondary_regime=secondary_regime,

            directional_bias=float(directional_bias),
            regime_confidence=float(regime_confidence),

            trend_strength=float(trend_strength),
            compression_strength=float(compression_strength),
            expansion_strength=float(expansion_strength),
            range_strength=float(range_strength),
            noise_strength=float(noise_strength),
            transition_strength=float(transition_strength),

            volatility_state=volatility_state,
            structure_state=structure_state,
            alignment_state=alignment_state,

            suitable_for_directional_analysis=suitable,
            caution_required=caution_required,

            reasons=tuple(reasons),
        )

    def _trend_strength(
        self,
        market: MarketIntelligenceSnapshot,
        directional_bias: float,
    ) -> float:
        structure_component = self._clip01(
            abs(
                market.context_5m.structure.trend_score
            )
        )

        alignment_component = market.alignment_score
        conviction_component = market.directional_conviction

        quality_component = (
            market.context_5m.trend_quality * 0.45
            + market.setup_1m.trend_quality * 0.35
            + market.base_30s.trend_quality * 0.20
        )

        bias_component = abs(directional_bias)

        return self._clip01(
            0.25 * structure_component
            + 0.25 * alignment_component
            + 0.20 * conviction_component
            + 0.20 * quality_component
            + 0.10 * bias_component
        )

    def _compression_strength(
        self,
        market: MarketIntelligenceSnapshot,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
    ) -> float:
        pattern_component = self._pattern_strength(
            patterns_by_timeframe,
            attribute="compression",
        )

        return self._clip01(
            0.65 * market.compression_pressure
            + 0.35 * pattern_component
        )

    def _expansion_strength(
        self,
        market: MarketIntelligenceSnapshot,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
    ) -> float:
        pattern_component = self._pattern_strength(
            patterns_by_timeframe,
            attribute="expansion",
        )

        breakout_component = self._pattern_strength(
            patterns_by_timeframe,
            attribute="breakout",
        )

        return self._clip01(
            0.55 * market.expansion_potential
            + 0.25 * pattern_component
            + 0.20 * breakout_component
        )

    def _noise_strength(
        self,
        market: MarketIntelligenceSnapshot,
        pattern_conflict: float,
    ) -> float:
        structure_noise = 0.0

        if market.context_5m.structure.structure_state == "TRANSITION":
            structure_noise = 0.60
        elif market.context_5m.structure.structure_state == "RANGE":
            structure_noise = 0.35

        return self._clip01(
            0.60 * market.noise_score
            + 0.20 * market.conflict_score
            + 0.10 * pattern_conflict
            + 0.10 * structure_noise
        )

    def _range_strength(
        self,
        market: MarketIntelligenceSnapshot,
        trend_strength: float,
        compression_strength: float,
        expansion_strength: float,
    ) -> float:
        structure_range = (
            1.0
            if market.context_5m.structure.structure_state == "RANGE"
            else 0.0
        )

        low_trend = 1.0 - trend_strength

        low_expansion = 1.0 - expansion_strength

        moderate_compression = (
            1.0 - abs(compression_strength - 0.45)
        )

        balanced_bias = (
            1.0 - min(
                abs(market.multi_timeframe_bias),
                1.0,
            )
        )

        return self._clip01(
            0.30 * structure_range
            + 0.25 * low_trend
            + 0.20 * low_expansion
            + 0.15 * balanced_bias
            + 0.10 * self._clip01(moderate_compression)
        )

    def _transition_strength(
        self,
        market: MarketIntelligenceSnapshot,
        pattern_conflict: float,
        trend_strength: float,
    ) -> float:
        structure_transition = (
            1.0
            if market.context_5m.structure.structure_state == "TRANSITION"
            else 0.0
        )

        choch_component = 0.0

        for timeframe in (
            market.base_30s,
            market.setup_1m,
            market.context_5m,
        ):
            if timeframe.structure.change_of_character != "NONE":
                choch_component = max(
                    choch_component,
                    1.0,
                )

        unstable_alignment = market.conflict_score

        medium_trend = 1.0 - abs(
            trend_strength - 0.50
        ) * 2.0

        return self._clip01(
            0.30 * structure_transition
            + 0.25 * choch_component
            + 0.25 * unstable_alignment
            + 0.10 * pattern_conflict
            + 0.10 * self._clip01(medium_trend)
        )

    @staticmethod
    def _volatility_state(
        tf_30: TimeframeIntelligence,
        tf_1m: TimeframeIntelligence,
        tf_5m: TimeframeIntelligence,
    ) -> str:
        normalized = (
            tf_30.technical.range_vs_atr * 0.45
            + tf_1m.technical.range_vs_atr * 0.35
            + tf_5m.technical.range_vs_atr * 0.20
        )

        if normalized < 0.65:
            return "LOW"

        if normalized < 1.25:
            return "NORMAL"

        if normalized < 2.00:
            return "HIGH"

        return "EXTREME"

    def _choose_primary_regime(
        self,
        directional_bias: float,
        trend_strength: float,
        compression_strength: float,
        expansion_strength: float,
        range_strength: float,
        noise_strength: float,
        transition_strength: float,
    ) -> tuple[str, float]:

        scores: dict[str, float] = {
            "COMPRESSION": compression_strength,
            "RANGE": range_strength,
            "HIGH_NOISE": noise_strength,
            "TRANSITION": transition_strength,
        }

        bullish_trend = (
            trend_strength
            if directional_bias > 0
            else 0.0
        )

        bearish_trend = (
            trend_strength
            if directional_bias < 0
            else 0.0
        )

        bullish_expansion = (
            expansion_strength
            if directional_bias > 0
            else 0.0
        )

        bearish_expansion = (
            expansion_strength
            if directional_bias < 0
            else 0.0
        )

        scores["BULLISH_TREND"] = bullish_trend
        scores["BEARISH_TREND"] = bearish_trend
        scores["BULLISH_EXPANSION"] = bullish_expansion
        scores["BEARISH_EXPANSION"] = bearish_expansion

        # Protective priority: very noisy markets should not be hidden behind
        # a visually strong but unreliable direction score.
        if noise_strength >= self.high_noise_threshold:
            return "HIGH_NOISE", noise_strength

        # Expansion gets priority over an ordinary trend when the impulse is
        # clearly active.
        if expansion_strength >= 0.72 and abs(directional_bias) >= 0.25:
            return (
                (
                    "BULLISH_EXPANSION"
                    if directional_bias > 0
                    else "BEARISH_EXPANSION"
                ),
                expansion_strength,
            )

        # Strong compression must be seen before a breakout is confirmed.
        if (
            compression_strength >= 0.70
            and expansion_strength < 0.60
        ):
            return "COMPRESSION", compression_strength

        # Strong directional structure.
        if (
            trend_strength >= self.trend_threshold
            and abs(directional_bias) >= 0.20
        ):
            return (
                (
                    "BULLISH_TREND"
                    if directional_bias > 0
                    else "BEARISH_TREND"
                ),
                trend_strength,
            )

        # Transition takes precedence over range when structural change is
        # clearly present.
        if transition_strength >= 0.62:
            return "TRANSITION", transition_strength

        if range_strength >= 0.55:
            return "RANGE", range_strength

        primary = max(
            scores,
            key=scores.get,
        )
        return primary, float(scores[primary])

    @staticmethod
    def _choose_secondary_regime(
        primary_regime: str,
        directional_bias: float,
        trend_strength: float,
        compression_strength: float,
        expansion_strength: float,
        range_strength: float,
        noise_strength: float,
        transition_strength: float,
    ) -> tuple[str, float]:
        scores = {
            "COMPRESSION": compression_strength,
            "RANGE": range_strength,
            "HIGH_NOISE": noise_strength,
            "TRANSITION": transition_strength,
            "BULLISH_TREND": (
                trend_strength
                if directional_bias > 0
                else 0.0
            ),
            "BEARISH_TREND": (
                trend_strength
                if directional_bias < 0
                else 0.0
            ),
            "BULLISH_EXPANSION": (
                expansion_strength
                if directional_bias > 0
                else 0.0
            ),
            "BEARISH_EXPANSION": (
                expansion_strength
                if directional_bias < 0
                else 0.0
            ),
        }

        scores.pop(primary_regime, None)

        if not scores:
            return "NONE", 0.0

        secondary = max(
            scores,
            key=scores.get,
        )

        return secondary, float(scores[secondary])

    def _regime_confidence(
        self,
        primary_score: float,
        secondary_score: float,
        market: MarketIntelligenceSnapshot,
        pattern_conflict: float,
    ) -> float:
        separation = self._clip01(
            primary_score - secondary_score + 0.50
        )

        evidence_quality = self._clip01(
            market.market_quality
        )

        agreement = self._clip01(
            1.0
            - (
                0.60 * market.conflict_score
                + 0.40 * pattern_conflict
            )
        )

        return self._clip01(
            0.45 * primary_score
            + 0.20 * separation
            + 0.20 * evidence_quality
            + 0.15 * agreement
        )

    @staticmethod
    def _alignment_state(
        alignment: float,
        conflict: float,
    ) -> str:
        if conflict >= 0.55:
            return "CONFLICTED"

        if alignment >= 0.70:
            return "ALIGNED"

        return "PARTIAL"

    @staticmethod
    def _suitable_for_directional_analysis(
        primary_regime: str,
        regime_confidence: float,
        market: MarketIntelligenceSnapshot,
        noise_strength: float,
    ) -> bool:
        directional_regimes = {
            "BULLISH_TREND",
            "BEARISH_TREND",
            "BULLISH_EXPANSION",
            "BEARISH_EXPANSION",
        }

        return (
            primary_regime in directional_regimes
            and regime_confidence >= 0.55
            and noise_strength < CONFIG.HIGH_NOISE_BLOCK_THRESHOLD
            and market.conflict_score < 0.60
            and market.readiness_state not in {
                "WARMUP",
                "BLOCKED_NOISE",
            }
        )

    @staticmethod
    def _aggregate_pattern_bias(
        snapshots: Iterable[PatternSnapshot],
    ) -> tuple[float, float]:
        snapshots = list(snapshots)

        if not snapshots:
            return 0.0, 0.0

        weighted_bias = 0.0
        total_weight = 0.0
        conflict = 0.0

        weights = {
            CONFIG.BASE_TIMEFRAME_SECONDS: 0.25,
            CONFIG.TIMEFRAME_1M_SECONDS: 0.35,
            CONFIG.TIMEFRAME_5M_SECONDS: 0.40,
        }

        for snapshot in snapshots:
            weight = weights.get(
                snapshot.timeframe_seconds,
                0.20,
            )

            quality_weight = max(
                snapshot.pattern_quality,
                0.10,
            )

            final_weight = weight * quality_weight

            weighted_bias += (
                snapshot.pattern_bias * final_weight
            )
            total_weight += final_weight

            conflict += (
                snapshot.conflict_score * weight
            )

        if total_weight <= 1e-12:
            return 0.0, 0.0

        return (
            RegimeDetector._clip(
                weighted_bias / total_weight,
                -1.0,
                1.0,
            ),
            RegimeDetector._clip01(conflict),
        )

    @staticmethod
    def _pattern_strength(
        snapshots: Mapping[int, PatternSnapshot],
        attribute: str,
    ) -> float:
        if not snapshots:
            return 0.0

        weights = {
            CONFIG.BASE_TIMEFRAME_SECONDS: 0.25,
            CONFIG.TIMEFRAME_1M_SECONDS: 0.35,
            CONFIG.TIMEFRAME_5M_SECONDS: 0.40,
        }

        weighted = 0.0
        total = 0.0

        for timeframe, snapshot in snapshots.items():
            signal = getattr(
                snapshot,
                attribute,
                None,
            )

            if signal is None:
                continue

            weight = weights.get(
                timeframe,
                0.20,
            )

            strength = (
                (signal.score / 100.0)
                * signal.confidence
            )

            weighted += strength * weight
            total += weight

        if total <= 1e-12:
            return 0.0

        return RegimeDetector._clip01(
            weighted / total
        )

    @staticmethod
    def _build_reasons(
        primary_regime: str,
        secondary_regime: str,
        directional_bias: float,
        trend_strength: float,
        compression_strength: float,
        expansion_strength: float,
        range_strength: float,
        noise_strength: float,
        transition_strength: float,
        volatility_state: str,
        alignment_state: str,
        market: MarketIntelligenceSnapshot,
    ) -> list[str]:
        reasons = [
            f"primary regime: {primary_regime.lower()}",
            f"secondary regime: {secondary_regime.lower()}",
            f"timeframe alignment: {alignment_state.lower()}",
            f"volatility: {volatility_state.lower()}",
        ]

        if directional_bias >= 0.25:
            reasons.append("directional regime bias is bullish")
        elif directional_bias <= -0.25:
            reasons.append("directional regime bias is bearish")
        else:
            reasons.append("directional regime bias is weak")

        if trend_strength >= 0.65:
            reasons.append("trend structure is strong")

        if compression_strength >= 0.65:
            reasons.append("compression pressure is elevated")

        if expansion_strength >= 0.65:
            reasons.append("expansion pressure is elevated")

        if range_strength >= 0.60:
            reasons.append("range behaviour is dominant")

        if transition_strength >= 0.60:
            reasons.append("market structure is changing")

        if noise_strength >= 0.65:
            reasons.append("noise/rejection risk is elevated")

        if market.context_5m.structure.change_of_character != "NONE":
            reasons.append(
                "5m change-of-character is active"
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
