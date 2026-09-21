from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence

from config import CONFIG
from data.pocket_connector import HistoricalCandle
from features.market_structure import MarketStructureSnapshot
from features.technical_features import TechnicalFeatureSnapshot


@dataclass(frozen=True, slots=True)
class PatternSignal:
    name: str
    direction: str               # "BULLISH" | "BEARISH" | "NEUTRAL"
    score: float                 # 0..100
    confidence: float            # 0..1
    stage: str                   # "BUILDING" | "CONFIRMED" | "FAILED"
    timeframe_seconds: int
    timestamp: float
    price: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PatternSnapshot:
    timestamp: float
    asset: str
    timeframe_seconds: int

    compression: Optional[PatternSignal]
    wick_cluster: Optional[PatternSignal]
    rejection: Optional[PatternSignal]
    fake_break: Optional[PatternSignal]
    breakout: Optional[PatternSignal]
    breakout_retest: Optional[PatternSignal]
    expansion: Optional[PatternSignal]

    dominant_pattern: Optional[PatternSignal]
    pattern_bias: float          # -1 bearish .. +1 bullish
    pattern_quality: float       # 0..1
    conflict_score: float        # 0..1

    all_patterns: tuple[PatternSignal, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "timeframe_seconds": self.timeframe_seconds,
            "compression": self.compression,
            "wick_cluster": self.wick_cluster,
            "rejection": self.rejection,
            "fake_break": self.fake_break,
            "breakout": self.breakout,
            "breakout_retest": self.breakout_retest,
            "expansion": self.expansion,
            "dominant_pattern": self.dominant_pattern,
            "pattern_bias": self.pattern_bias,
            "pattern_quality": self.pattern_quality,
            "conflict_score": self.conflict_score,
            "all_patterns": self.all_patterns,
        }


class PatternEngine:
    """
    Detects price-action patterns from CLOSED candles only.

    Main OTC-oriented behaviours:
    - 3..7 candle wick clusters around the same area.
    - Compression before expansion.
    - Strong rejection.
    - Fake breakout / liquidity sweep.
    - Real breakout.
    - Breakout + retest.
    - Expansion impulse.

    Indicators are supportive only. Pattern logic is primarily price-action
    and structure based.
    """

    def __init__(
        self,
        compression_lookback: int = CONFIG.COMPRESSION_LOOKBACK,
        wick_cluster_lookback: int = CONFIG.WICK_CLUSTER_LOOKBACK,
        fake_break_lookback: int = CONFIG.FAKE_BREAK_LOOKBACK,
    ) -> None:
        if compression_lookback < 3:
            raise ValueError("compression_lookback must be >= 3.")
        if wick_cluster_lookback < 3:
            raise ValueError("wick_cluster_lookback must be >= 3.")
        if fake_break_lookback < 5:
            raise ValueError("fake_break_lookback must be >= 5.")

        self.compression_lookback = int(compression_lookback)
        self.wick_cluster_lookback = int(wick_cluster_lookback)
        self.fake_break_lookback = int(fake_break_lookback)

    def analyze(
        self,
        candles: Sequence[HistoricalCandle] | Iterable[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> PatternSnapshot:
        candles = list(candles)
        if not candles:
            raise ValueError("At least one candle is required.")

        self._validate_alignment(
            candles=candles,
            technical=technical,
            structure=structure,
        )

        patterns: list[PatternSignal] = []

        compression = self._detect_compression(
            candles,
            technical,
            structure,
        )
        if compression:
            patterns.append(compression)

        wick_cluster = self._detect_wick_cluster(
            candles,
            technical,
            structure,
        )
        if wick_cluster:
            patterns.append(wick_cluster)

        rejection = self._detect_rejection(
            candles,
            technical,
            structure,
        )
        if rejection:
            patterns.append(rejection)

        fake_break = self._detect_fake_break(
            candles,
            technical,
            structure,
        )
        if fake_break:
            patterns.append(fake_break)

        breakout = self._detect_breakout(
            candles,
            technical,
            structure,
        )
        if breakout:
            patterns.append(breakout)

        breakout_retest = self._detect_breakout_retest(
            candles,
            technical,
            structure,
        )
        if breakout_retest:
            patterns.append(breakout_retest)

        expansion = self._detect_expansion(
            candles,
            technical,
            structure,
        )
        if expansion:
            patterns.append(expansion)

        dominant = self._dominant_pattern(patterns)
        bias, conflict = self._pattern_bias(patterns)

        if patterns:
            quality = sum(
                p.confidence * (p.score / 100.0)
                for p in patterns
            ) / len(patterns)

            quality *= (1.0 - 0.60 * conflict)
            quality = self._clip01(quality)
        else:
            quality = 0.0

        return PatternSnapshot(
            timestamp=float(candles[-1].timestamp),
            asset=candles[-1].asset,
            timeframe_seconds=int(candles[-1].timeframe_seconds),

            compression=compression,
            wick_cluster=wick_cluster,
            rejection=rejection,
            fake_break=fake_break,
            breakout=breakout,
            breakout_retest=breakout_retest,
            expansion=expansion,

            dominant_pattern=dominant,
            pattern_bias=float(self._clip(bias, -1.0, 1.0)),
            pattern_quality=float(quality),
            conflict_score=float(conflict),

            all_patterns=tuple(
                sorted(
                    patterns,
                    key=lambda p: (p.score, p.confidence),
                    reverse=True,
                )
            ),
        )

    def _detect_compression(
        self,
        candles: Sequence[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> Optional[PatternSignal]:
        if len(candles) < 3:
            return None

        window = candles[
            -min(len(candles), self.compression_lookback):
        ]

        widths = [
            max(c.high - c.low, 0.0)
            for c in window
        ]

        current_span = max(c.high for c in window) - min(c.low for c in window)

        atr = max(technical.atr, 1e-12)
        normalized_span = current_span / (atr * max(len(window) ** 0.5, 1.0))

        small_candles = sum(
            1 for width in widths
            if width <= atr
        ) / len(widths)

        wick_heavy = sum(
            1
            for c in window
            if self._wick_ratio(c) >= 0.45
        ) / len(window)

        score = self._clip01(
            0.45 * (1.0 - min(normalized_span, 1.0))
            + 0.35 * small_candles
            + 0.20 * wick_heavy
        )

        score = max(
            score,
            self._clip01(
                1.0 - min(structure.compression_ratio, 1.0)
            ),
        )

        if score < 0.55:
            return None

        stage = (
            "CONFIRMED"
            if score >= 0.72
            else "BUILDING"
        )

        return PatternSignal(
            name="COMPRESSION",
            direction="NEUTRAL",
            score=float(score * 100.0),
            confidence=float(score),
            stage=stage,
            timeframe_seconds=technical.timeframe_seconds,
            timestamp=technical.timestamp,
            price=technical.close,
            reasons=(
                f"{len(window)}-candle range is compressed",
                f"normalized span={normalized_span:.2f}",
                f"small-candle ratio={small_candles:.2f}",
            ),
        )

    def _detect_wick_cluster(
        self,
        candles: Sequence[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> Optional[PatternSignal]:
        if len(candles) < 3:
            return None

        window = candles[
            -min(
                len(candles),
                max(3, min(self.wick_cluster_lookback, 7)),
            ):
        ]

        atr = max(technical.atr, 1e-12)
        tolerance = max(
            atr * 0.35,
            technical.close * 0.00002,
        )

        upper_levels = [
            c.high
            for c in window
            if self._upper_wick_ratio(c) >= 0.35
        ]
        lower_levels = [
            c.low
            for c in window
            if self._lower_wick_ratio(c) >= 0.35
        ]

        upper_cluster = self._cluster_strength(
            upper_levels,
            tolerance,
            len(window),
        )
        lower_cluster = self._cluster_strength(
            lower_levels,
            tolerance,
            len(window),
        )

        best = max(
            upper_cluster,
            lower_cluster,
        )

        if best < 0.50:
            return None

        if upper_cluster > lower_cluster:
            direction = "BEARISH"
            side = "upper"
        elif lower_cluster > upper_cluster:
            direction = "BULLISH"
            side = "lower"
        else:
            direction = "NEUTRAL"
            side = "both"

        compression_bonus = self._clip01(
            1.0 - min(structure.compression_ratio, 1.0)
        )

        score = self._clip01(
            0.75 * best
            + 0.25 * compression_bonus
        )

        return PatternSignal(
            name="WICK_CLUSTER",
            direction=direction,
            score=float(score * 100.0),
            confidence=float(score),
            stage=(
                "CONFIRMED"
                if score >= 0.70
                else "BUILDING"
            ),
            timeframe_seconds=technical.timeframe_seconds,
            timestamp=technical.timestamp,
            price=technical.close,
            reasons=(
                f"{side}-wick cluster across {len(window)} candles",
                f"upper cluster={upper_cluster:.2f}",
                f"lower cluster={lower_cluster:.2f}",
            ),
        )

    def _detect_rejection(
        self,
        candles: Sequence[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> Optional[PatternSignal]:
        latest = candles[-1]

        upper_ratio = self._upper_wick_ratio(latest)
        lower_ratio = self._lower_wick_ratio(latest)

        upper_strength = self._clip01(
            upper_ratio / max(CONFIG.REJECTION_WICK_RATIO, 1e-9)
        )
        lower_strength = self._clip01(
            lower_ratio / max(CONFIG.REJECTION_WICK_RATIO, 1e-9)
        )

        if max(upper_strength, lower_strength) < 0.80:
            return None

        if lower_strength > upper_strength:
            direction = "BULLISH"
            wick_strength = lower_strength
            close_strength = technical.close_position
        else:
            direction = "BEARISH"
            wick_strength = upper_strength
            close_strength = 1.0 - technical.close_position

        location_bonus = 0.0

        if (
            direction == "BULLISH"
            and structure.nearest_support is not None
            and structure.support_distance is not None
        ):
            location_bonus = self._clip01(
                1.0
                - (
                    structure.support_distance
                    / max(technical.atr * 2.0, 1e-12)
                )
            )

        if (
            direction == "BEARISH"
            and structure.nearest_resistance is not None
            and structure.resistance_distance is not None
        ):
            location_bonus = self._clip01(
                1.0
                - (
                    structure.resistance_distance
                    / max(technical.atr * 2.0, 1e-12)
                )
            )

        score = self._clip01(
            0.55 * wick_strength
            + 0.25 * close_strength
            + 0.20 * location_bonus
        )

        if score < 0.55:
            return None

        return PatternSignal(
            name="REJECTION",
            direction=direction,
            score=float(score * 100.0),
            confidence=float(score),
            stage="CONFIRMED",
            timeframe_seconds=technical.timeframe_seconds,
            timestamp=technical.timestamp,
            price=technical.close,
            reasons=(
                f"dominant {direction.lower()} rejection wick",
                f"upper wick ratio={upper_ratio:.2f}",
                f"lower wick ratio={lower_ratio:.2f}",
                f"location bonus={location_bonus:.2f}",
            ),
        )

    def _detect_fake_break(
        self,
        candles: Sequence[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> Optional[PatternSignal]:
        if len(candles) < 6:
            return None

        latest = candles[-1]
        prior = candles[
            -min(len(candles), self.fake_break_lookback + 1):-1
        ]

        if len(prior) < 5:
            return None

        prior_high = max(c.high for c in prior)
        prior_low = min(c.low for c in prior)

        atr = max(technical.atr, 1e-12)
        tolerance = atr * 0.10

        bearish_sweep = (
            latest.high > prior_high + tolerance
            and latest.close < prior_high
        )

        bullish_sweep = (
            latest.low < prior_low - tolerance
            and latest.close > prior_low
        )

        if not bearish_sweep and not bullish_sweep:
            return None

        if bearish_sweep:
            direction = "BEARISH"
            penetration = (
                latest.high - prior_high
            ) / atr
            rejection = self._upper_wick_ratio(latest)
            close_reentry = self._clip01(
                (prior_high - latest.close) / atr
            )
        else:
            direction = "BULLISH"
            penetration = (
                prior_low - latest.low
            ) / atr
            rejection = self._lower_wick_ratio(latest)
            close_reentry = self._clip01(
                (latest.close - prior_low) / atr
            )

        penetration_score = self._clip01(
            penetration / 0.50
        )

        rejection_score = self._clip01(
            rejection / max(CONFIG.REJECTION_WICK_RATIO, 1e-9)
        )

        score = self._clip01(
            0.35 * penetration_score
            + 0.40 * rejection_score
            + 0.25 * close_reentry
        )

        if score < 0.55:
            return None

        return PatternSignal(
            name="FAKE_BREAK",
            direction=direction,
            score=float(score * 100.0),
            confidence=float(score),
            stage="CONFIRMED",
            timeframe_seconds=technical.timeframe_seconds,
            timestamp=technical.timestamp,
            price=technical.close,
            reasons=(
                "price swept a prior range extreme and closed back inside",
                f"penetration={penetration:.2f} ATR",
                f"rejection={rejection:.2f}",
            ),
        )

    def _detect_breakout(
        self,
        candles: Sequence[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> Optional[PatternSignal]:
        if len(candles) < 6:
            return None

        latest = candles[-1]
        prior = candles[-6:-1]

        prior_high = max(c.high for c in prior)
        prior_low = min(c.low for c in prior)

        atr = max(technical.atr, 1e-12)
        buffer = atr * 0.10

        bullish = (
            latest.close > prior_high + buffer
        )
        bearish = (
            latest.close < prior_low - buffer
        )

        if not bullish and not bearish:
            return None

        direction = (
            "BULLISH"
            if bullish
            else "BEARISH"
        )

        body = technical.body_ratio
        expansion = self._clip01(
            technical.range_vs_atr
            / max(CONFIG.EXPANSION_ATR_MULTIPLIER, 1e-9)
        )

        if direction == "BULLISH":
            close_quality = technical.close_position
        else:
            close_quality = 1.0 - technical.close_position

        structure_bonus = 1.0 if (
            structure.break_of_structure == direction
        ) else 0.4

        score = self._clip01(
            0.30 * body
            + 0.30 * expansion
            + 0.25 * close_quality
            + 0.15 * structure_bonus
        )

        if score < 0.55:
            return None

        return PatternSignal(
            name="BREAKOUT",
            direction=direction,
            score=float(score * 100.0),
            confidence=float(score),
            stage=(
                "CONFIRMED"
                if score >= 0.70
                else "BUILDING"
            ),
            timeframe_seconds=technical.timeframe_seconds,
            timestamp=technical.timestamp,
            price=technical.close,
            reasons=(
                f"{direction.lower()} close outside recent range",
                f"body ratio={body:.2f}",
                f"range/ATR={technical.range_vs_atr:.2f}",
            ),
        )

    def _detect_breakout_retest(
        self,
        candles: Sequence[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> Optional[PatternSignal]:
        if len(candles) < 8:
            return None

        latest = candles[-1]
        prior = candles[-8:-2]
        breakout_candle = candles[-2]

        prior_high = max(c.high for c in prior)
        prior_low = min(c.low for c in prior)

        atr = max(technical.atr, 1e-12)
        tolerance = atr * 0.25

        bullish_break = breakout_candle.close > prior_high
        bearish_break = breakout_candle.close < prior_low

        if bullish_break:
            touched = latest.low <= prior_high + tolerance
            held = latest.close >= prior_high
            if touched and held:
                direction = "BULLISH"
                retest_quality = self._clip01(
                    1.0 - abs(latest.low - prior_high) / max(atr, 1e-12)
                )
            else:
                return None

        elif bearish_break:
            touched = latest.high >= prior_low - tolerance
            held = latest.close <= prior_low
            if touched and held:
                direction = "BEARISH"
                retest_quality = self._clip01(
                    1.0 - abs(latest.high - prior_low) / max(atr, 1e-12)
                )
            else:
                return None

        else:
            return None

        rejection = (
            self._lower_wick_ratio(latest)
            if direction == "BULLISH"
            else self._upper_wick_ratio(latest)
        )

        score = self._clip01(
            0.60 * retest_quality
            + 0.40 * rejection
        )

        if score < 0.50:
            return None

        return PatternSignal(
            name="BREAKOUT_RETEST",
            direction=direction,
            score=float(score * 100.0),
            confidence=float(score),
            stage="CONFIRMED",
            timeframe_seconds=technical.timeframe_seconds,
            timestamp=technical.timestamp,
            price=technical.close,
            reasons=(
                "breakout level was retested and held",
                f"retest quality={retest_quality:.2f}",
                f"rejection={rejection:.2f}",
            ),
        )

    def _detect_expansion(
        self,
        candles: Sequence[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> Optional[PatternSignal]:
        if technical.range_vs_atr < 1.10:
            return None

        body_strength = self._clip01(
            technical.body_ratio
            / max(CONFIG.STRONG_BODY_RATIO, 1e-9)
        )

        range_strength = self._clip01(
            technical.range_vs_atr
            / max(CONFIG.EXPANSION_ATR_MULTIPLIER, 1e-9)
        )

        activity_strength = self._clip01(
            technical.tick_activity_ratio / 2.0
        )

        if technical.direction > 0:
            direction = "BULLISH"
            close_strength = technical.close_position
        elif technical.direction < 0:
            direction = "BEARISH"
            close_strength = 1.0 - technical.close_position
        else:
            return None

        score = self._clip01(
            0.35 * range_strength
            + 0.30 * body_strength
            + 0.20 * close_strength
            + 0.15 * activity_strength
        )

        if score < 0.58:
            return None

        return PatternSignal(
            name="EXPANSION",
            direction=direction,
            score=float(score * 100.0),
            confidence=float(score),
            stage="CONFIRMED",
            timeframe_seconds=technical.timeframe_seconds,
            timestamp=technical.timestamp,
            price=technical.close,
            reasons=(
                f"{direction.lower()} range expansion",
                f"range/ATR={technical.range_vs_atr:.2f}",
                f"body ratio={technical.body_ratio:.2f}",
            ),
        )

    @staticmethod
    def _dominant_pattern(
        patterns: Sequence[PatternSignal],
    ) -> Optional[PatternSignal]:
        if not patterns:
            return None

        directional = [
            p for p in patterns
            if p.direction != "NEUTRAL"
        ]

        pool = directional or list(patterns)

        return max(
            pool,
            key=lambda p: (
                p.score * p.confidence,
                p.score,
            ),
        )

    @staticmethod
    def _pattern_bias(
        patterns: Sequence[PatternSignal],
    ) -> tuple[float, float]:
        directional = [
            p for p in patterns
            if p.direction in {"BULLISH", "BEARISH"}
        ]

        if not directional:
            return 0.0, 0.0

        bullish = sum(
            (p.score / 100.0) * p.confidence
            for p in directional
            if p.direction == "BULLISH"
        )

        bearish = sum(
            (p.score / 100.0) * p.confidence
            for p in directional
            if p.direction == "BEARISH"
        )

        total = bullish + bearish

        if total <= 1e-12:
            return 0.0, 0.0

        bias = (bullish - bearish) / total
        conflict = (2.0 * min(bullish, bearish)) / total

        return (
            PatternEngine._clip(bias, -1.0, 1.0),
            PatternEngine._clip01(conflict),
        )

    @staticmethod
    def _cluster_strength(
        levels: Sequence[float],
        tolerance: float,
        window_size: int,
    ) -> float:
        if len(levels) < 3:
            return 0.0

        best_count = 0

        for level in levels:
            count = sum(
                1
                for other in levels
                if abs(other - level) <= tolerance
            )
            best_count = max(best_count, count)

        count_score = best_count / max(window_size, 1)

        spread = max(levels) - min(levels)
        spread_score = 1.0 - min(
            spread / max(tolerance * 4.0, 1e-12),
            1.0,
        )

        return PatternEngine._clip01(
            0.75 * count_score
            + 0.25 * spread_score
        )

    @staticmethod
    def _wick_ratio(
        candle: HistoricalCandle,
    ) -> float:
        return (
            PatternEngine._upper_wick_ratio(candle)
            + PatternEngine._lower_wick_ratio(candle)
        )

    @staticmethod
    def _upper_wick_ratio(
        candle: HistoricalCandle,
    ) -> float:
        candle_range = candle.high - candle.low

        if candle_range <= 0:
            return 0.0

        upper = candle.high - max(
            candle.open,
            candle.close,
        )

        return PatternEngine._clip01(
            upper / candle_range
        )

    @staticmethod
    def _lower_wick_ratio(
        candle: HistoricalCandle,
    ) -> float:
        candle_range = candle.high - candle.low

        if candle_range <= 0:
            return 0.0

        lower = min(
            candle.open,
            candle.close,
        ) - candle.low

        return PatternEngine._clip01(
            lower / candle_range
        )

    @staticmethod
    def _validate_alignment(
        candles: Sequence[HistoricalCandle],
        technical: TechnicalFeatureSnapshot,
        structure: MarketStructureSnapshot,
    ) -> None:
        latest = candles[-1]

        if latest.asset != technical.asset:
            raise ValueError(
                "Technical snapshot asset does not match candles."
            )

        if latest.asset != structure.asset:
            raise ValueError(
                "Structure snapshot asset does not match candles."
            )

        if latest.timeframe_seconds != technical.timeframe_seconds:
            raise ValueError(
                "Technical snapshot timeframe does not match candles."
            )

        if latest.timeframe_seconds != structure.timeframe_seconds:
            raise ValueError(
                "Structure snapshot timeframe does not match candles."
            )

        if latest.timestamp != technical.timestamp:
            raise ValueError(
                "Technical snapshot timestamp does not match latest candle."
            )

        if latest.timestamp != structure.timestamp:
            raise ValueError(
                "Structure snapshot timestamp does not match latest candle."
            )

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
