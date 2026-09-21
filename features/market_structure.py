from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Iterable, Optional, Sequence

from config import CONFIG
from data.pocket_connector import HistoricalCandle
from features.technical_features import TechnicalFeatureSnapshot


@dataclass(frozen=True, slots=True)
class SwingPoint:
    index: int
    timestamp: float
    price: float
    kind: str          # "HIGH" | "LOW"
    label: str         # "HH" | "LH" | "HL" | "LL" | "H" | "L"


@dataclass(frozen=True, slots=True)
class PriceZone:
    center: float
    lower: float
    upper: float
    kind: str          # "SUPPORT" | "RESISTANCE"
    touches: int
    strength: float    # 0..1
    last_touch_time: float


@dataclass(frozen=True, slots=True)
class MarketStructureSnapshot:
    timestamp: float
    asset: str
    timeframe_seconds: int
    close: float

    structure_state: str
    trend_score: float            # -1 bearish .. +1 bullish
    structure_confidence: float   # 0..1

    last_swing_high: Optional[SwingPoint]
    previous_swing_high: Optional[SwingPoint]
    last_swing_low: Optional[SwingPoint]
    previous_swing_low: Optional[SwingPoint]

    nearest_support: Optional[PriceZone]
    nearest_resistance: Optional[PriceZone]
    support_distance: Optional[float]
    resistance_distance: Optional[float]

    break_of_structure: str       # "BULLISH" | "BEARISH" | "NONE"
    change_of_character: str      # "BULLISH" | "BEARISH" | "NONE"

    range_high: float
    range_low: float
    range_position: float         # 0..1
    compression_ratio: float

    swing_highs: tuple[SwingPoint, ...] = field(default_factory=tuple)
    swing_lows: tuple[SwingPoint, ...] = field(default_factory=tuple)
    support_zones: tuple[PriceZone, ...] = field(default_factory=tuple)
    resistance_zones: tuple[PriceZone, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "timeframe_seconds": self.timeframe_seconds,
            "close": self.close,
            "structure_state": self.structure_state,
            "trend_score": self.trend_score,
            "structure_confidence": self.structure_confidence,
            "last_swing_high": self.last_swing_high,
            "previous_swing_high": self.previous_swing_high,
            "last_swing_low": self.last_swing_low,
            "previous_swing_low": self.previous_swing_low,
            "nearest_support": self.nearest_support,
            "nearest_resistance": self.nearest_resistance,
            "support_distance": self.support_distance,
            "resistance_distance": self.resistance_distance,
            "break_of_structure": self.break_of_structure,
            "change_of_character": self.change_of_character,
            "range_high": self.range_high,
            "range_low": self.range_low,
            "range_position": self.range_position,
            "compression_ratio": self.compression_ratio,
            "swing_highs": self.swing_highs,
            "swing_lows": self.swing_lows,
            "support_zones": self.support_zones,
            "resistance_zones": self.resistance_zones,
        }


class MarketStructureEngine:
    """
    Extracts market structure from CLOSED candles only.

    It identifies:
    - confirmed swing highs/lows,
    - HH / HL / LH / LL structure,
    - support and resistance zones,
    - break of structure (BOS),
    - change of character (CHoCH),
    - range position and compression.

    It deliberately does not produce BUY/SELL advice.
    """

    def __init__(
        self,
        swing_left: int = 2,
        swing_right: int = 2,
        structure_lookback: int = CONFIG.STRUCTURE_LOOKBACK,
        zone_lookback: int = CONFIG.SUPPORT_RESISTANCE_LOOKBACK,
    ) -> None:
        if swing_left < 1 or swing_right < 1:
            raise ValueError("swing_left and swing_right must be >= 1.")
        if structure_lookback < 5:
            raise ValueError("structure_lookback must be >= 5.")
        if zone_lookback < 10:
            raise ValueError("zone_lookback must be >= 10.")

        self.swing_left = int(swing_left)
        self.swing_right = int(swing_right)
        self.structure_lookback = int(structure_lookback)
        self.zone_lookback = int(zone_lookback)

    def analyze(
        self,
        candles: Sequence[HistoricalCandle] | Iterable[HistoricalCandle],
        technical: Optional[TechnicalFeatureSnapshot] = None,
    ) -> MarketStructureSnapshot:
        candles = list(candles)
        if not candles:
            raise ValueError("At least one closed candle is required.")

        self._validate_sequence(candles)

        latest = candles[-1]
        recent_structure = candles[-min(len(candles), self.structure_lookback):]
        recent_zones = candles[-min(len(candles), self.zone_lookback):]

        raw_highs, raw_lows = self._detect_swings(candles)

        swing_highs = self._label_highs(raw_highs)
        swing_lows = self._label_lows(raw_lows)

        last_high = swing_highs[-1] if swing_highs else None
        prev_high = swing_highs[-2] if len(swing_highs) >= 2 else None
        last_low = swing_lows[-1] if swing_lows else None
        prev_low = swing_lows[-2] if len(swing_lows) >= 2 else None

        atr = (
            float(technical.atr)
            if technical is not None and technical.atr > 0
            else self._fallback_atr(recent_zones)
        )

        tolerance = self._zone_tolerance(
            candles=recent_zones,
            atr=atr,
            current_price=latest.close,
        )

        support_zones = self._build_zones(
            points=[p for p in swing_lows if p.index >= len(candles) - self.zone_lookback],
            kind="SUPPORT",
            tolerance=tolerance,
            latest_timestamp=latest.timestamp,
        )

        resistance_zones = self._build_zones(
            points=[p for p in swing_highs if p.index >= len(candles) - self.zone_lookback],
            kind="RESISTANCE",
            tolerance=tolerance,
            latest_timestamp=latest.timestamp,
        )

        # If the confirmed swing set is still sparse during warmup, add the
        # recent structural extremes as low-confidence fallback zones.
        if not support_zones and recent_zones:
            low_candle = min(recent_zones, key=lambda c: c.low)
            support_zones = (
                PriceZone(
                    center=float(low_candle.low),
                    lower=float(low_candle.low - tolerance),
                    upper=float(low_candle.low + tolerance),
                    kind="SUPPORT",
                    touches=1,
                    strength=0.25,
                    last_touch_time=float(low_candle.timestamp),
                ),
            )

        if not resistance_zones and recent_zones:
            high_candle = max(recent_zones, key=lambda c: c.high)
            resistance_zones = (
                PriceZone(
                    center=float(high_candle.high),
                    lower=float(high_candle.high - tolerance),
                    upper=float(high_candle.high + tolerance),
                    kind="RESISTANCE",
                    touches=1,
                    strength=0.25,
                    last_touch_time=float(high_candle.timestamp),
                ),
            )

        nearest_support = self._nearest_support(
            support_zones,
            latest.close,
        )
        nearest_resistance = self._nearest_resistance(
            resistance_zones,
            latest.close,
        )

        support_distance = (
            latest.close - nearest_support.center
            if nearest_support is not None
            else None
        )
        resistance_distance = (
            nearest_resistance.center - latest.close
            if nearest_resistance is not None
            else None
        )

        break_of_structure = self._detect_bos(
            latest_close=latest.close,
            previous_close=candles[-2].close if len(candles) >= 2 else latest.close,
            last_high=last_high,
            last_low=last_low,
            tolerance=tolerance,
        )

        structure_state, trend_score, confidence = self._classify_structure(
            last_high=last_high,
            previous_high=prev_high,
            last_low=last_low,
            previous_low=prev_low,
            technical=technical,
        )

        change_of_character = self._detect_choch(
            structure_state=structure_state,
            break_of_structure=break_of_structure,
        )

        range_high = max(c.high for c in recent_structure)
        range_low = min(c.low for c in recent_structure)
        range_width = max(range_high - range_low, 0.0)

        if range_width > 0:
            range_position = (
                (latest.close - range_low) / range_width
            )
        else:
            range_position = 0.5

        compression_ratio = self._compression_ratio(
            candles=recent_structure,
            atr=atr,
        )

        return MarketStructureSnapshot(
            timestamp=float(latest.timestamp),
            asset=latest.asset,
            timeframe_seconds=int(latest.timeframe_seconds),
            close=float(latest.close),

            structure_state=structure_state,
            trend_score=float(self._clip(trend_score, -1.0, 1.0)),
            structure_confidence=float(self._clip(confidence, 0.0, 1.0)),

            last_swing_high=last_high,
            previous_swing_high=prev_high,
            last_swing_low=last_low,
            previous_swing_low=prev_low,

            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            support_distance=(
                float(max(support_distance, 0.0))
                if support_distance is not None
                else None
            ),
            resistance_distance=(
                float(max(resistance_distance, 0.0))
                if resistance_distance is not None
                else None
            ),

            break_of_structure=break_of_structure,
            change_of_character=change_of_character,

            range_high=float(range_high),
            range_low=float(range_low),
            range_position=float(self._clip(range_position, 0.0, 1.0)),
            compression_ratio=float(self._clip(compression_ratio, 0.0, 2.0)),

            swing_highs=tuple(swing_highs[-12:]),
            swing_lows=tuple(swing_lows[-12:]),
            support_zones=tuple(support_zones[:8]),
            resistance_zones=tuple(resistance_zones[:8]),
        )

    def _detect_swings(
        self,
        candles: Sequence[HistoricalCandle],
    ) -> tuple[list[SwingPoint], list[SwingPoint]]:
        highs: list[SwingPoint] = []
        lows: list[SwingPoint] = []

        start = self.swing_left
        stop = len(candles) - self.swing_right

        for i in range(start, max(start, stop)):
            current = candles[i]

            left = candles[i - self.swing_left:i]
            right = candles[i + 1:i + 1 + self.swing_right]

            if len(left) < self.swing_left or len(right) < self.swing_right:
                continue

            is_high = (
                all(current.high >= c.high for c in left)
                and all(current.high > c.high for c in right)
            )

            is_low = (
                all(current.low <= c.low for c in left)
                and all(current.low < c.low for c in right)
            )

            if is_high:
                highs.append(
                    SwingPoint(
                        index=i,
                        timestamp=float(current.timestamp),
                        price=float(current.high),
                        kind="HIGH",
                        label="H",
                    )
                )

            if is_low:
                lows.append(
                    SwingPoint(
                        index=i,
                        timestamp=float(current.timestamp),
                        price=float(current.low),
                        kind="LOW",
                        label="L",
                    )
                )

        return highs, lows

    @staticmethod
    def _label_highs(
        highs: Sequence[SwingPoint],
    ) -> list[SwingPoint]:
        result: list[SwingPoint] = []
        previous: Optional[SwingPoint] = None

        for point in highs:
            if previous is None:
                label = "H"
            elif point.price > previous.price:
                label = "HH"
            else:
                label = "LH"

            labeled = SwingPoint(
                index=point.index,
                timestamp=point.timestamp,
                price=point.price,
                kind="HIGH",
                label=label,
            )
            result.append(labeled)
            previous = labeled

        return result

    @staticmethod
    def _label_lows(
        lows: Sequence[SwingPoint],
    ) -> list[SwingPoint]:
        result: list[SwingPoint] = []
        previous: Optional[SwingPoint] = None

        for point in lows:
            if previous is None:
                label = "L"
            elif point.price > previous.price:
                label = "HL"
            else:
                label = "LL"

            labeled = SwingPoint(
                index=point.index,
                timestamp=point.timestamp,
                price=point.price,
                kind="LOW",
                label=label,
            )
            result.append(labeled)
            previous = labeled

        return result

    @staticmethod
    def _classify_structure(
        last_high: Optional[SwingPoint],
        previous_high: Optional[SwingPoint],
        last_low: Optional[SwingPoint],
        previous_low: Optional[SwingPoint],
        technical: Optional[TechnicalFeatureSnapshot],
    ) -> tuple[str, float, float]:

        high_signal = 0
        low_signal = 0
        confirmed_parts = 0

        if last_high is not None and previous_high is not None:
            confirmed_parts += 1
            if last_high.price > previous_high.price:
                high_signal = 1
            elif last_high.price < previous_high.price:
                high_signal = -1

        if last_low is not None and previous_low is not None:
            confirmed_parts += 1
            if last_low.price > previous_low.price:
                low_signal = 1
            elif last_low.price < previous_low.price:
                low_signal = -1

        structure_signal = (high_signal + low_signal) / 2.0

        technical_signal = 0.0
        if technical is not None and technical.warmup_complete:
            if technical.ema_spread_normalized > 0:
                technical_signal = min(
                    abs(technical.ema_spread_normalized),
                    1.0,
                )
            elif technical.ema_spread_normalized < 0:
                technical_signal = -min(
                    abs(technical.ema_spread_normalized),
                    1.0,
                )

        if confirmed_parts == 2:
            trend_score = 0.80 * structure_signal + 0.20 * technical_signal
            confidence = 0.85
        elif confirmed_parts == 1:
            trend_score = 0.65 * structure_signal + 0.35 * technical_signal
            confidence = 0.55
        else:
            trend_score = technical_signal * 0.50
            confidence = 0.30 if technical is not None else 0.15

        if high_signal == 1 and low_signal == 1:
            state = "BULLISH"
        elif high_signal == -1 and low_signal == -1:
            state = "BEARISH"
        elif high_signal == 0 and low_signal == 0:
            state = "RANGE"
        elif high_signal != low_signal:
            state = "TRANSITION"
        elif trend_score > 0.20:
            state = "BULLISH"
        elif trend_score < -0.20:
            state = "BEARISH"
        else:
            state = "RANGE"

        return state, trend_score, confidence

    @staticmethod
    def _detect_bos(
        latest_close: float,
        previous_close: float,
        last_high: Optional[SwingPoint],
        last_low: Optional[SwingPoint],
        tolerance: float,
    ) -> str:

        if (
            last_high is not None
            and latest_close > last_high.price + tolerance
            and previous_close <= last_high.price + tolerance
        ):
            return "BULLISH"

        if (
            last_low is not None
            and latest_close < last_low.price - tolerance
            and previous_close >= last_low.price - tolerance
        ):
            return "BEARISH"

        return "NONE"

    @staticmethod
    def _detect_choch(
        structure_state: str,
        break_of_structure: str,
    ) -> str:
        if structure_state == "BEARISH" and break_of_structure == "BULLISH":
            return "BULLISH"

        if structure_state == "BULLISH" and break_of_structure == "BEARISH":
            return "BEARISH"

        return "NONE"

    @staticmethod
    def _build_zones(
        points: Sequence[SwingPoint],
        kind: str,
        tolerance: float,
        latest_timestamp: float,
    ) -> tuple[PriceZone, ...]:
        if not points:
            return tuple()

        clusters: list[list[SwingPoint]] = []

        for point in sorted(points, key=lambda p: p.price):
            matched = False

            for cluster in clusters:
                center = sum(p.price for p in cluster) / len(cluster)

                if abs(point.price - center) <= tolerance:
                    cluster.append(point)
                    matched = True
                    break

            if not matched:
                clusters.append([point])

        zones: list[PriceZone] = []

        for cluster in clusters:
            center = sum(p.price for p in cluster) / len(cluster)
            touches = len(cluster)
            last_touch = max(p.timestamp for p in cluster)

            recency_denominator = max(
                latest_timestamp - min(p.timestamp for p in cluster),
                1.0,
            )
            recency = 1.0 - min(
                (latest_timestamp - last_touch) / recency_denominator,
                1.0,
            )

            touch_strength = min(touches / 4.0, 1.0)
            strength = 0.75 * touch_strength + 0.25 * recency

            zones.append(
                PriceZone(
                    center=float(center),
                    lower=float(center - tolerance),
                    upper=float(center + tolerance),
                    kind=kind,
                    touches=touches,
                    strength=float(min(max(strength, 0.0), 1.0)),
                    last_touch_time=float(last_touch),
                )
            )

        zones.sort(
            key=lambda zone: (
                zone.strength,
                zone.touches,
                zone.last_touch_time,
            ),
            reverse=True,
        )

        return tuple(zones)

    @staticmethod
    def _nearest_support(
        zones: Sequence[PriceZone],
        price: float,
    ) -> Optional[PriceZone]:
        candidates = [
            zone for zone in zones
            if zone.center <= price
        ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda zone: price - zone.center,
        )

    @staticmethod
    def _nearest_resistance(
        zones: Sequence[PriceZone],
        price: float,
    ) -> Optional[PriceZone]:
        candidates = [
            zone for zone in zones
            if zone.center >= price
        ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda zone: zone.center - price,
        )

    @staticmethod
    def _fallback_atr(
        candles: Sequence[HistoricalCandle],
    ) -> float:
        if not candles:
            return 0.0

        ranges = [
            max(c.high - c.low, 0.0)
            for c in candles
        ]

        return float(
            sum(ranges) / len(ranges)
        )

    @staticmethod
    def _zone_tolerance(
        candles: Sequence[HistoricalCandle],
        atr: float,
        current_price: float,
    ) -> float:
        ranges = [
            max(c.high - c.low, 0.0)
            for c in candles
        ]

        median_range = median(ranges) if ranges else 0.0

        return float(
            max(
                atr * 0.25,
                median_range * 0.25,
                abs(current_price) * 0.00002,
                1e-9,
            )
        )

    @staticmethod
    def _compression_ratio(
        candles: Sequence[HistoricalCandle],
        atr: float,
    ) -> float:
        if not candles:
            return 1.0

        lookback = min(
            len(candles),
            CONFIG.COMPRESSION_LOOKBACK,
        )
        window = candles[-lookback:]

        local_high = max(c.high for c in window)
        local_low = min(c.low for c in window)
        width = max(local_high - local_low, 0.0)

        if atr <= 0:
            return 1.0

        expected_width = atr * max(lookback ** 0.5, 1.0)

        if expected_width <= 0:
            return 1.0

        return width / expected_width

    @staticmethod
    def _clip(
        value: float,
        low: float,
        high: float,
    ) -> float:
        return min(max(float(value), low), high)

    @staticmethod
    def _validate_sequence(
        candles: Sequence[HistoricalCandle],
    ) -> None:
        if not candles:
            raise ValueError("Candle sequence cannot be empty.")

        asset = candles[0].asset
        timeframe = candles[0].timeframe_seconds
        previous_timestamp: Optional[float] = None

        for candle in candles:
            if candle.asset != asset:
                raise ValueError(
                    "All candles must belong to the same asset."
                )

            if candle.timeframe_seconds != timeframe:
                raise ValueError(
                    "All candles must belong to the same timeframe."
                )

            if candle.timestamp <= 0:
                raise ValueError(
                    "Candle timestamp must be positive."
                )

            if min(
                candle.open,
                candle.high,
                candle.low,
                candle.close,
            ) <= 0:
                raise ValueError(
                    "Candle prices must be positive."
                )

            if candle.high < max(
                candle.open,
                candle.close,
                candle.low,
            ):
                raise ValueError(
                    "Invalid candle high."
                )

            if candle.low > min(
                candle.open,
                candle.close,
                candle.high,
            ):
                raise ValueError(
                    "Invalid candle low."
                )

            if (
                previous_timestamp is not None
                and candle.timestamp <= previous_timestamp
            ):
                raise ValueError(
                    "Candles must be strictly chronological."
                )

            previous_timestamp = candle.timestamp
