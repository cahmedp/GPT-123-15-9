from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Optional, Sequence

from config import CONFIG
from data.pocket_connector import HistoricalCandle
from features.market_structure import (
    MarketStructureEngine,
    MarketStructureSnapshot,
)
from features.technical_features import (
    TechnicalFeatureEngine,
    TechnicalFeatureSnapshot,
)


@dataclass(frozen=True, slots=True)
class TimeframeIntelligence:
    timeframe_seconds: int
    technical: TechnicalFeatureSnapshot
    structure: MarketStructureSnapshot

    directional_pressure: float
    trend_quality: float
    noise_score: float
    expansion_score: float
    compression_score: float
    rejection_score: float
    momentum_score: float
    location_score: float
    quality_score: float

    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class MarketIntelligenceSnapshot:
    timestamp: float
    asset: str
    price: float

    base_30s: TimeframeIntelligence
    setup_1m: TimeframeIntelligence
    context_5m: TimeframeIntelligence

    multi_timeframe_bias: float
    alignment_score: float
    conflict_score: float

    bullish_pressure: float
    bearish_pressure: float
    directional_conviction: float

    compression_pressure: float
    expansion_potential: float
    rejection_pressure: float
    noise_score: float

    market_quality: float
    context_state: str
    readiness_state: str

    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "price": self.price,
            "multi_timeframe_bias": self.multi_timeframe_bias,
            "alignment_score": self.alignment_score,
            "conflict_score": self.conflict_score,
            "bullish_pressure": self.bullish_pressure,
            "bearish_pressure": self.bearish_pressure,
            "directional_conviction": self.directional_conviction,
            "compression_pressure": self.compression_pressure,
            "expansion_potential": self.expansion_potential,
            "rejection_pressure": self.rejection_pressure,
            "noise_score": self.noise_score,
            "market_quality": self.market_quality,
            "context_state": self.context_state,
            "readiness_state": self.readiness_state,
            "reasons": self.reasons,
        }


class MarketIntelligenceEngine:
    """
    High-level market understanding layer.

    It combines:
    - 30-second trigger context,
    - 1-minute setup context,
    - 5-minute market context,
    - candle anatomy,
    - trend/momentum,
    - structure,
    - support/resistance location,
    - compression/expansion,
    - wick/rejection behaviour,
    - noise.

    This engine does NOT execute trades and does not produce the final
    BUY/SELL decision. Its output becomes evidence for the multi-agent brain.
    """

    REQUIRED_TIMEFRAMES = (
        CONFIG.BASE_TIMEFRAME_SECONDS,
        CONFIG.TIMEFRAME_1M_SECONDS,
        CONFIG.TIMEFRAME_5M_SECONDS,
    )

    def __init__(
        self,
        feature_engine: Optional[TechnicalFeatureEngine] = None,
        structure_engine: Optional[MarketStructureEngine] = None,
    ) -> None:
        self.feature_engine = feature_engine or TechnicalFeatureEngine()
        self.structure_engine = structure_engine or MarketStructureEngine()

    def analyze(
        self,
        candles_by_timeframe: Mapping[
            int,
            Sequence[HistoricalCandle] | Iterable[HistoricalCandle],
        ],
        tick_activity_by_timeframe: Optional[
            Mapping[int, Sequence[float] | Iterable[float]]
        ] = None,
    ) -> MarketIntelligenceSnapshot:
        prepared = self._prepare_timeframes(candles_by_timeframe)

        activity_map = tick_activity_by_timeframe or {}

        tf_30 = self._analyze_timeframe(
            prepared[CONFIG.BASE_TIMEFRAME_SECONDS],
            activity_map.get(CONFIG.BASE_TIMEFRAME_SECONDS),
        )
        tf_1m = self._analyze_timeframe(
            prepared[CONFIG.TIMEFRAME_1M_SECONDS],
            activity_map.get(CONFIG.TIMEFRAME_1M_SECONDS),
        )
        tf_5m = self._analyze_timeframe(
            prepared[CONFIG.TIMEFRAME_5M_SECONDS],
            activity_map.get(CONFIG.TIMEFRAME_5M_SECONDS),
        )

        latest = prepared[CONFIG.BASE_TIMEFRAME_SECONDS][-1]

        weighted_bias = self._weighted_bias(
            tf_30= tf_30,
            tf_1m= tf_1m,
            tf_5m= tf_5m,
        )

        alignment_score = self._alignment_score(
            tf_30,
            tf_1m,
            tf_5m,
        )

        conflict_score = self._conflict_score(
            tf_30,
            tf_1m,
            tf_5m,
        )

        bullish_pressure = self._bullish_pressure(
            tf_30,
            tf_1m,
            tf_5m,
        )

        bearish_pressure = self._bearish_pressure(
            tf_30,
            tf_1m,
            tf_5m,
        )

        directional_conviction = self._clip01(
            abs(weighted_bias)
            * (0.55 + 0.45 * alignment_score)
            * (1.0 - 0.65 * conflict_score)
        )

        compression_pressure = self._clip01(
            (
                tf_30.compression_score * 0.50
                + tf_1m.compression_score * 0.35
                + tf_5m.compression_score * 0.15
            )
        )

        expansion_potential = self._clip01(
            (
                tf_30.expansion_score * 0.45
                + tf_1m.expansion_score * 0.35
                + tf_5m.expansion_score * 0.20
            )
            * (0.65 + 0.35 * alignment_score)
        )

        rejection_pressure = self._clip01(
            tf_30.rejection_score * 0.50
            + tf_1m.rejection_score * 0.35
            + tf_5m.rejection_score * 0.15
        )

        noise_score = self._clip01(
            tf_30.noise_score * 0.50
            + tf_1m.noise_score * 0.30
            + tf_5m.noise_score * 0.20
        )

        market_quality = self._clip01(
            (
                tf_30.quality_score * 0.35
                + tf_1m.quality_score * 0.35
                + tf_5m.quality_score * 0.30
            )
            * (1.0 - 0.55 * conflict_score)
        )

        context_state = self._context_state(
            bias=weighted_bias,
            alignment=alignment_score,
            compression=compression_pressure,
            expansion=expansion_potential,
            noise=noise_score,
        )

        readiness_state = self._readiness_state(
            tf_30=tf_30,
            tf_1m=tf_1m,
            tf_5m=tf_5m,
            market_quality=market_quality,
            conflict=conflict_score,
            noise=noise_score,
        )

        reasons = self._build_reasons(
            tf_30=tf_30,
            tf_1m=tf_1m,
            tf_5m=tf_5m,
            bias=weighted_bias,
            alignment=alignment_score,
            conflict=conflict_score,
            compression=compression_pressure,
            expansion=expansion_potential,
            noise=noise_score,
            readiness=readiness_state,
        )

        return MarketIntelligenceSnapshot(
            timestamp=float(latest.timestamp),
            asset=latest.asset,
            price=float(latest.close),

            base_30s=tf_30,
            setup_1m=tf_1m,
            context_5m=tf_5m,

            multi_timeframe_bias=float(
                self._clip(weighted_bias, -1.0, 1.0)
            ),
            alignment_score=float(alignment_score),
            conflict_score=float(conflict_score),

            bullish_pressure=float(bullish_pressure),
            bearish_pressure=float(bearish_pressure),
            directional_conviction=float(directional_conviction),

            compression_pressure=float(compression_pressure),
            expansion_potential=float(expansion_potential),
            rejection_pressure=float(rejection_pressure),
            noise_score=float(noise_score),

            market_quality=float(market_quality),
            context_state=context_state,
            readiness_state=readiness_state,

            reasons=tuple(reasons),
        )

    def _analyze_timeframe(
        self,
        candles: Sequence[HistoricalCandle],
        tick_activity: Optional[
            Sequence[float] | Iterable[float]
        ],
    ) -> TimeframeIntelligence:
        technical = self.feature_engine.calculate(
            candles=candles,
            tick_activity=tick_activity,
        )

        structure = self.structure_engine.analyze(
            candles=candles,
            technical=technical,
        )

        directional_pressure = self._directional_pressure(
            technical,
            structure,
        )

        trend_quality = self._trend_quality(
            technical,
            structure,
        )

        noise_score = self._noise_score(
            technical,
            structure,
        )

        expansion_score = self._expansion_score(
            technical,
            structure,
        )

        compression_score = self._compression_score(
            technical,
            structure,
        )

        rejection_score = self._rejection_score(
            technical,
        )

        momentum_score = self._momentum_score(
            technical,
        )

        location_score = self._location_score(
            technical,
            structure,
        )

        quality_score = self._clip01(
            0.25 * trend_quality
            + 0.20 * momentum_score
            + 0.20 * location_score
            + 0.20 * (1.0 - noise_score)
            + 0.15 * structure.structure_confidence
        )

        notes = self._timeframe_notes(
            technical=technical,
            structure=structure,
            directional_pressure=directional_pressure,
            noise_score=noise_score,
            expansion_score=expansion_score,
            compression_score=compression_score,
        )

        return TimeframeIntelligence(
            timeframe_seconds=technical.timeframe_seconds,
            technical=technical,
            structure=structure,

            directional_pressure=float(
                self._clip(directional_pressure, -1.0, 1.0)
            ),
            trend_quality=float(trend_quality),
            noise_score=float(noise_score),
            expansion_score=float(expansion_score),
            compression_score=float(compression_score),
            rejection_score=float(rejection_score),
            momentum_score=float(momentum_score),
            location_score=float(location_score),
            quality_score=float(quality_score),

            notes=tuple(notes),
        )

    @staticmethod
    def _directional_pressure(
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> float:
        ema_component = MarketIntelligenceEngine._clip(
            technical.ema_spread_normalized,
            -1.0,
            1.0,
        )

        momentum_raw = (
            technical.return_1 * 0.45
            + technical.return_3 * 0.35
            + technical.return_5 * 0.20
        )

        atr_pct = (
            technical.atr / technical.close
            if technical.close > 0
            else 0.0
        )

        if atr_pct > 0:
            momentum_component = MarketIntelligenceEngine._clip(
                momentum_raw / atr_pct,
                -1.0,
                1.0,
            )
        else:
            momentum_component = 0.0

        candle_component = 0.0
        if technical.direction > 0:
            candle_component = technical.body_ratio * (
                0.50 + 0.50 * technical.close_position
            )
        elif technical.direction < 0:
            candle_component = -technical.body_ratio * (
                0.50 + 0.50 * (1.0 - technical.close_position)
            )

        score = (
            0.40 * structure.trend_score
            + 0.25 * ema_component
            + 0.20 * momentum_component
            + 0.15 * candle_component
        )

        return MarketIntelligenceEngine._clip(
            score,
            -1.0,
            1.0,
        )

    @staticmethod
    def _trend_quality(
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> float:
        efficiency = technical.efficiency_ratio
        structure_strength = abs(structure.trend_score)
        ema_strength = min(
            abs(technical.ema_spread_normalized),
            1.0,
        )

        agreement = 1.0

        if (
            structure.trend_score > 0
            and technical.ema_spread_normalized < 0
        ) or (
            structure.trend_score < 0
            and technical.ema_spread_normalized > 0
        ):
            agreement = 0.35

        return MarketIntelligenceEngine._clip01(
            (
                0.40 * efficiency
                + 0.35 * structure_strength
                + 0.25 * ema_strength
            )
            * agreement
        )

    @staticmethod
    def _noise_score(
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> float:
        total_wicks = (
            technical.upper_wick_ratio
            + technical.lower_wick_ratio
        )

        wick_noise = MarketIntelligenceEngine._clip01(
            total_wicks
        )

        low_efficiency_noise = (
            1.0 - technical.efficiency_ratio
        )

        structure_noise = 0.0
        if structure.structure_state in {
            "RANGE",
            "TRANSITION",
        }:
            structure_noise = 0.75

        alternating_component = 0.0
        if abs(structure.trend_score) < 0.20:
            alternating_component = 0.65

        score = (
            0.35 * wick_noise
            + 0.30 * low_efficiency_noise
            + 0.20 * structure_noise
            + 0.15 * alternating_component
        )

        return MarketIntelligenceEngine._clip01(
            score
        )

    @staticmethod
    def _expansion_score(
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> float:
        range_component = MarketIntelligenceEngine._clip01(
            technical.range_vs_atr
            / max(
                CONFIG.EXPANSION_ATR_MULTIPLIER,
                1e-9,
            )
        )

        body_component = technical.body_ratio

        activity_component = MarketIntelligenceEngine._clip01(
            technical.tick_activity_ratio / 2.0
        )

        break_component = (
            1.0
            if structure.break_of_structure != "NONE"
            else 0.0
        )

        return MarketIntelligenceEngine._clip01(
            0.35 * range_component
            + 0.30 * body_component
            + 0.20 * activity_component
            + 0.15 * break_component
        )

    @staticmethod
    def _compression_score(
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> float:
        structure_ratio = structure.compression_ratio

        if structure_ratio <= 0:
            structure_component = 1.0
        else:
            structure_component = MarketIntelligenceEngine._clip01(
                (
                    CONFIG.COMPRESSION_RANGE_RATIO
                    / max(structure_ratio, 1e-9)
                )
            )

        low_range_component = MarketIntelligenceEngine._clip01(
            1.0 - min(technical.range_vs_atr, 1.0)
        )

        low_efficiency_component = MarketIntelligenceEngine._clip01(
            1.0 - technical.efficiency_ratio
        )

        return MarketIntelligenceEngine._clip01(
            0.50 * structure_component
            + 0.30 * low_range_component
            + 0.20 * low_efficiency_component
        )

    @staticmethod
    def _rejection_score(
        technical: TechnicalFeatureSnapshot,
    ) -> float:
        dominant_wick = max(
            technical.upper_wick_ratio,
            technical.lower_wick_ratio,
        )

        close_reaction = max(
            technical.close_position,
            1.0 - technical.close_position,
        )

        wick_component = MarketIntelligenceEngine._clip01(
            dominant_wick
            / max(
                CONFIG.REJECTION_WICK_RATIO,
                1e-9,
            )
        )

        return MarketIntelligenceEngine._clip01(
            0.70 * wick_component
            + 0.30 * close_reaction
        )

    @staticmethod
    def _momentum_score(
        technical: TechnicalFeatureSnapshot,
    ) -> float:
        atr = max(technical.atr, 1e-12)

        impulse = (
            abs(technical.momentum_1) * 0.45
            + abs(technical.momentum_3) * 0.35
            + abs(technical.momentum_5) * 0.20
        )

        normalized = impulse / atr

        return MarketIntelligenceEngine._clip01(
            normalized
        )

    @staticmethod
    def _location_score(
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> float:
        atr = max(technical.atr, 1e-12)

        scores: list[float] = []

        if structure.support_distance is not None:
            support_proximity = 1.0 - min(
                structure.support_distance / (atr * 2.0),
                1.0,
            )
            scores.append(support_proximity)

        if structure.resistance_distance is not None:
            resistance_proximity = 1.0 - min(
                structure.resistance_distance / (atr * 2.0),
                1.0,
            )
            scores.append(resistance_proximity)

        if not scores:
            return 0.5

        return MarketIntelligenceEngine._clip01(
            max(scores)
        )

    @staticmethod
    def _weighted_bias(
        tf_30: TimeframeIntelligence,
        tf_1m: TimeframeIntelligence,
        tf_5m: TimeframeIntelligence,
    ) -> float:
        # 5m defines context, 1m defines setup, 30s defines trigger.
        return MarketIntelligenceEngine._clip(
            (
                tf_30.directional_pressure * 0.45
                + tf_1m.directional_pressure * 0.35
                + tf_5m.directional_pressure * 0.20
            ),
            -1.0,
            1.0,
        )

    @staticmethod
    def _alignment_score(
        *timeframes: TimeframeIntelligence,
    ) -> float:
        values = [
            tf.directional_pressure
            for tf in timeframes
        ]

        signs = [
            1 if value > 0.10
            else -1 if value < -0.10
            else 0
            for value in values
        ]

        non_zero = [
            sign for sign in signs if sign != 0
        ]

        if not non_zero:
            return 0.0

        dominant = (
            1
            if sum(non_zero) > 0
            else -1
        )

        directional_agreement = (
            sum(
                1
                for sign in non_zero
                if sign == dominant
            )
            / len(non_zero)
        )

        magnitude_consistency = (
            1.0
            - min(
                max(values) - min(values),
                2.0,
            ) / 2.0
        )

        return MarketIntelligenceEngine._clip01(
            0.75 * directional_agreement
            + 0.25 * magnitude_consistency
        )

    @staticmethod
    def _conflict_score(
        *timeframes: TimeframeIntelligence,
    ) -> float:
        if len(timeframes) != 3:
            return 0.0

        tf_30, tf_1m, tf_5m = timeframes

        execution_setup_conflict = abs(
            tf_30.directional_pressure
            - tf_1m.directional_pressure
        ) / 2.0

        context_conflict = abs(
            tf_30.directional_pressure
            - tf_5m.directional_pressure
        ) / 2.0

        # 30s and 1m disagreement is execution risk.
        # 5m disagreement is context risk only.
        conflict = (
            execution_setup_conflict * 0.75
            + context_conflict * 0.25
        )

        return MarketIntelligenceEngine._clip01(
            conflict
        )

    @staticmethod
    def _bullish_pressure(
        *timeframes: TimeframeIntelligence,
    ) -> float:
        weights = (0.45, 0.35, 0.20)

        return MarketIntelligenceEngine._clip01(
            sum(
                max(tf.directional_pressure, 0.0) * weight
                for tf, weight in zip(timeframes, weights)
            )
        )

    @staticmethod
    def _bearish_pressure(
        *timeframes: TimeframeIntelligence,
    ) -> float:
        weights = (0.45, 0.35, 0.20)

        return MarketIntelligenceEngine._clip01(
            sum(
                max(-tf.directional_pressure, 0.0) * weight
                for tf, weight in zip(timeframes, weights)
            )
        )

    @staticmethod
    def _context_state(
        bias: float,
        alignment: float,
        compression: float,
        expansion: float,
        noise: float,
    ) -> str:
        if noise >= 0.75:
            return "HIGH_NOISE"

        if compression >= 0.68 and expansion < 0.55:
            return "COMPRESSION"

        if expansion >= 0.70 and abs(bias) >= 0.30:
            return (
                "BULLISH_EXPANSION"
                if bias > 0
                else "BEARISH_EXPANSION"
            )

        if alignment >= 0.70 and bias >= 0.25:
            return "BULLISH_CONTEXT"

        if alignment >= 0.70 and bias <= -0.25:
            return "BEARISH_CONTEXT"

        if abs(bias) <= 0.15:
            return "BALANCED"

        return "MIXED_CONTEXT"

    @staticmethod
    def _readiness_state(
        tf_30: TimeframeIntelligence,
        tf_1m: TimeframeIntelligence,
        tf_5m: TimeframeIntelligence,
        market_quality: float,
        conflict: float,
        noise: float,
    ) -> str:
        warm = (
            tf_30.technical.warmup_complete
            and tf_1m.technical.warmup_complete
            and tf_5m.technical.warmup_complete
        )

        if not warm:
            return "WARMUP"

        if noise >= CONFIG.HIGH_NOISE_BLOCK_THRESHOLD:
            return "BLOCKED_NOISE"

        if conflict >= 0.60:
            return "WAIT_CONFLICT"

        if market_quality < 0.40:
            return "WAIT_LOW_QUALITY"

        if market_quality >= 0.70 and conflict <= 0.30:
            return "READY"

        return "OBSERVE"

    @staticmethod
    def _timeframe_notes(
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
        directional_pressure: float,
        noise_score: float,
        expansion_score: float,
        compression_score: float,
    ) -> list[str]:
        notes: list[str] = []

        if directional_pressure >= 0.35:
            notes.append("bullish directional pressure")
        elif directional_pressure <= -0.35:
            notes.append("bearish directional pressure")
        else:
            notes.append("weak directional pressure")

        if structure.break_of_structure != "NONE":
            notes.append(
                f"{structure.break_of_structure.lower()} break of structure"
            )

        if structure.change_of_character != "NONE":
            notes.append(
                f"{structure.change_of_character.lower()} change of character"
            )

        if compression_score >= 0.65:
            notes.append("compression detected")

        if expansion_score >= 0.70:
            notes.append("range expansion detected")

        if noise_score >= 0.70:
            notes.append("high market noise")

        if (
            technical.upper_wick_ratio
            >= CONFIG.REJECTION_WICK_RATIO
        ):
            notes.append("strong upper-wick rejection")

        if (
            technical.lower_wick_ratio
            >= CONFIG.REJECTION_WICK_RATIO
        ):
            notes.append("strong lower-wick rejection")

        return notes

    @staticmethod
    def _build_reasons(
        tf_30: TimeframeIntelligence,
        tf_1m: TimeframeIntelligence,
        tf_5m: TimeframeIntelligence,
        bias: float,
        alignment: float,
        conflict: float,
        compression: float,
        expansion: float,
        noise: float,
        readiness: str,
    ) -> list[str]:
        reasons: list[str] = []

        if bias >= 0.30:
            reasons.append("multi-timeframe pressure leans bullish")
        elif bias <= -0.30:
            reasons.append("multi-timeframe pressure leans bearish")
        else:
            reasons.append("multi-timeframe directional pressure is limited")

        if alignment >= 0.70:
            reasons.append("30s, 1m and 5m are well aligned")
        elif conflict >= 0.50:
            reasons.append("timeframes are materially conflicting")

        if compression >= 0.65:
            reasons.append("price is building compression")

        if expansion >= 0.70:
            reasons.append("expansion energy is already elevated")

        if noise >= 0.70:
            reasons.append("wick/noise conditions are elevated")

        if tf_5m.structure.structure_state in {"BULLISH", "BEARISH"}:
            reasons.append(
                f"5m structure is {tf_5m.structure.structure_state.lower()}"
            )

        if tf_1m.structure.break_of_structure != "NONE":
            reasons.append(
                f"1m BOS is {tf_1m.structure.break_of_structure.lower()}"
            )

        if tf_30.structure.change_of_character != "NONE":
            reasons.append(
                f"30s CHoCH is {tf_30.structure.change_of_character.lower()}"
            )

        reasons.append(
            f"market readiness: {readiness.lower()}"
        )

        return reasons

    @classmethod
    def _prepare_timeframes(
        cls,
        candles_by_timeframe: Mapping[
            int,
            Sequence[HistoricalCandle] | Iterable[HistoricalCandle],
        ],
    ) -> Dict[int, list[HistoricalCandle]]:
        prepared: Dict[int, list[HistoricalCandle]] = {}

        for timeframe in cls.REQUIRED_TIMEFRAMES:
            raw = candles_by_timeframe.get(timeframe)

            if raw is None:
                raise ValueError(
                    f"Missing required timeframe: {timeframe}s."
                )

            candles = list(raw)

            if not candles:
                raise ValueError(
                    f"Timeframe {timeframe}s has no candles."
                )

            if any(
                candle.timeframe_seconds != timeframe
                for candle in candles
            ):
                raise ValueError(
                    f"Timeframe {timeframe}s contains mismatched candles."
                )

            prepared[timeframe] = candles

        assets = {
            candles[-1].asset
            for candles in prepared.values()
        }

        if len(assets) != 1:
            raise ValueError(
                "All timeframes must belong to the same asset."
            )

        return prepared

    @staticmethod
    def _clip01(value: float) -> float:
        return min(max(float(value), 0.0), 1.0)

    @staticmethod
    def _clip(
        value: float,
        low: float,
        high: float,
    ) -> float:
        return min(max(float(value), low), high)