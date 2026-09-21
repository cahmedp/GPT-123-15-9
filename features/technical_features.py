from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from statistics import fmean, pstdev
from typing import Iterable, Optional, Sequence

import numpy as np

from config import CONFIG
from data.pocket_connector import HistoricalCandle


@dataclass(frozen=True, slots=True)
class TechnicalFeatureSnapshot:
    """
    Numerical description of the latest CLOSED candle and its recent history.

    This object contains observations/features only.
    It does not contain BUY/SELL decisions.
    """

    timestamp: float
    asset: str
    timeframe_seconds: int

    # Latest OHLC
    open: float
    high: float
    low: float
    close: float

    # Candle anatomy
    candle_range: float
    body_size: float
    body_ratio: float
    upper_wick: float
    lower_wick: float
    upper_wick_ratio: float
    lower_wick_ratio: float
    close_position: float
    direction: int

    # Volatility / range
    atr: float
    average_range: float
    range_vs_atr: float
    realized_volatility: float
    price_zscore: float

    # Trend / momentum
    ema_fast: float
    ema_slow: float
    ema_spread: float
    ema_spread_normalized: float
    rsi: float
    momentum_1: float
    momentum_3: float
    momentum_5: float
    return_1: float
    return_3: float
    return_5: float
    efficiency_ratio: float

    # Activity
    tick_activity: float
    tick_activity_ratio: float

    # Quality
    history_size: int
    warmup_complete: bool

    def as_dict(self) -> dict[str, float | int | str | bool]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }


class TechnicalFeatureEngine:
    """
    Converts closed OHLC candles into stable numerical features.

    Design principles:
    - Indicators are supporting evidence, never the final decision.
    - No future leakage: each snapshot uses only candles available up to that
      timestamp.
    - Works with Pocket Option OTC 30s, 1m and 5m candle streams.
    - Returns safe neutral defaults during warmup instead of producing NaN.
    """

    def __init__(
        self,
        atr_period: int = CONFIG.ATR_PERIOD,
        rsi_period: int = CONFIG.RSI_PERIOD,
        ema_fast_period: int = CONFIG.EMA_FAST_PERIOD,
        ema_slow_period: int = CONFIG.EMA_SLOW_PERIOD,
        volatility_lookback: int = CONFIG.STRUCTURE_LOOKBACK,
    ) -> None:
        for name, value in (
            ("atr_period", atr_period),
            ("rsi_period", rsi_period),
            ("ema_fast_period", ema_fast_period),
            ("ema_slow_period", ema_slow_period),
            ("volatility_lookback", volatility_lookback),
        ):
            if int(value) <= 0:
                raise ValueError(f"{name} must be greater than zero.")

        if ema_fast_period >= ema_slow_period:
            raise ValueError(
                "ema_fast_period must be smaller than ema_slow_period."
            )

        self.atr_period = int(atr_period)
        self.rsi_period = int(rsi_period)
        self.ema_fast_period = int(ema_fast_period)
        self.ema_slow_period = int(ema_slow_period)
        self.volatility_lookback = int(volatility_lookback)

        self.minimum_history = max(
            self.atr_period + 1,
            self.rsi_period + 1,
            self.ema_slow_period,
            6,
        )

    def calculate(
        self,
        candles: Sequence[HistoricalCandle] | Iterable[HistoricalCandle],
        tick_activity: Optional[Sequence[float] | Iterable[float]] = None,
    ) -> TechnicalFeatureSnapshot:
        """
        Calculate one feature snapshot for the latest CLOSED candle.

        `tick_activity` is optional and should contain activity values aligned
        with the candle sequence. If unavailable, the activity features remain
        neutral and do not influence later reasoning.
        """

        candles = list(candles)
        if not candles:
            raise ValueError("At least one closed candle is required.")

        self._validate_sequence(candles)

        activity = self._normalize_activity(
            tick_activity=tick_activity,
            required_length=len(candles),
        )

        latest = candles[-1]

        opens = np.asarray([c.open for c in candles], dtype=np.float64)
        highs = np.asarray([c.high for c in candles], dtype=np.float64)
        lows = np.asarray([c.low for c in candles], dtype=np.float64)
        closes = np.asarray([c.close for c in candles], dtype=np.float64)

        candle_range = max(latest.high - latest.low, 0.0)
        body_size = abs(latest.close - latest.open)

        if candle_range > 0:
            body_ratio = body_size / candle_range
            upper_wick = latest.high - max(latest.open, latest.close)
            lower_wick = min(latest.open, latest.close) - latest.low
            upper_wick_ratio = upper_wick / candle_range
            lower_wick_ratio = lower_wick / candle_range
            close_position = (latest.close - latest.low) / candle_range
        else:
            body_ratio = 0.0
            upper_wick = 0.0
            lower_wick = 0.0
            upper_wick_ratio = 0.0
            lower_wick_ratio = 0.0
            close_position = 0.5

        direction = self._direction(latest.open, latest.close)

        true_ranges = self._true_ranges(highs, lows, closes)
        atr = self._rolling_mean_last(
            true_ranges,
            self.atr_period,
        )

        ranges = highs - lows
        average_range = self._rolling_mean_last(
            ranges,
            self.atr_period,
        )

        range_vs_atr = (
            candle_range / atr
            if atr > 0
            else 0.0
        )

        ema_fast = self._ema_last(
            closes,
            self.ema_fast_period,
        )
        ema_slow = self._ema_last(
            closes,
            self.ema_slow_period,
        )

        ema_spread = ema_fast - ema_slow
        ema_spread_normalized = (
            ema_spread / atr
            if atr > 0
            else 0.0
        )

        rsi = self._rsi_last(
            closes,
            self.rsi_period,
        )

        momentum_1 = self._momentum(closes, 1)
        momentum_3 = self._momentum(closes, 3)
        momentum_5 = self._momentum(closes, 5)

        return_1 = self._simple_return(closes, 1)
        return_3 = self._simple_return(closes, 3)
        return_5 = self._simple_return(closes, 5)

        realized_volatility = self._realized_volatility(
            closes,
            self.volatility_lookback,
        )

        price_zscore = self._zscore_last(
            closes,
            self.volatility_lookback,
        )

        efficiency_ratio = self._efficiency_ratio(
            closes,
            self.volatility_lookback,
        )

        latest_activity = activity[-1]
        activity_mean = self._rolling_mean_last(
            np.asarray(activity, dtype=np.float64),
            CONFIG.TICK_ACTIVITY_LOOKBACK,
        )

        tick_activity_ratio = (
            latest_activity / activity_mean
            if activity_mean > 0
            else 1.0
        )

        warmup_complete = (
            len(candles) >= self.minimum_history
        )

        return TechnicalFeatureSnapshot(
            timestamp=float(latest.timestamp),
            asset=latest.asset,
            timeframe_seconds=int(latest.timeframe_seconds),

            open=float(latest.open),
            high=float(latest.high),
            low=float(latest.low),
            close=float(latest.close),

            candle_range=float(candle_range),
            body_size=float(body_size),
            body_ratio=float(self._clip01(body_ratio)),
            upper_wick=float(max(upper_wick, 0.0)),
            lower_wick=float(max(lower_wick, 0.0)),
            upper_wick_ratio=float(self._clip01(upper_wick_ratio)),
            lower_wick_ratio=float(self._clip01(lower_wick_ratio)),
            close_position=float(self._clip01(close_position)),
            direction=int(direction),

            atr=float(max(atr, 0.0)),
            average_range=float(max(average_range, 0.0)),
            range_vs_atr=float(max(range_vs_atr, 0.0)),
            realized_volatility=float(max(realized_volatility, 0.0)),
            price_zscore=float(price_zscore),

            ema_fast=float(ema_fast),
            ema_slow=float(ema_slow),
            ema_spread=float(ema_spread),
            ema_spread_normalized=float(ema_spread_normalized),
            rsi=float(min(max(rsi, 0.0), 100.0)),
            momentum_1=float(momentum_1),
            momentum_3=float(momentum_3),
            momentum_5=float(momentum_5),
            return_1=float(return_1),
            return_3=float(return_3),
            return_5=float(return_5),
            efficiency_ratio=float(self._clip01(efficiency_ratio)),

            tick_activity=float(max(latest_activity, 0.0)),
            tick_activity_ratio=float(max(tick_activity_ratio, 0.0)),

            history_size=len(candles),
            warmup_complete=warmup_complete,
        )

    def calculate_series(
        self,
        candles: Sequence[HistoricalCandle] | Iterable[HistoricalCandle],
        tick_activity: Optional[Sequence[float] | Iterable[float]] = None,
        include_warmup: bool = False,
    ) -> list[TechnicalFeatureSnapshot]:
        """
        Build chronological snapshots for backtesting/replay.

        Every snapshot is calculated from a prefix ending at that candle,
        therefore no future candle can leak into an older feature row.
        """

        candles = list(candles)
        if not candles:
            return []

        self._validate_sequence(candles)

        activity = self._normalize_activity(
            tick_activity=tick_activity,
            required_length=len(candles),
        )

        snapshots: list[TechnicalFeatureSnapshot] = []

        for end in range(1, len(candles) + 1):
            snapshot = self.calculate(
                candles=candles[:end],
                tick_activity=activity[:end],
            )

            if include_warmup or snapshot.warmup_complete:
                snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def candle_weight(
        snapshot: TechnicalFeatureSnapshot,
    ) -> float:
        """
        Structural weight of a single candle in [0, 1].

        It rewards:
        - meaningful body size,
        - directional close location,
        - range expansion relative to ATR.

        This is a feature-quality measurement, not a trade signal.
        """

        body_component = snapshot.body_ratio

        if snapshot.direction > 0:
            close_component = snapshot.close_position
        elif snapshot.direction < 0:
            close_component = 1.0 - snapshot.close_position
        else:
            close_component = 0.5

        expansion_component = min(
            snapshot.range_vs_atr / max(
                CONFIG.EXPANSION_ATR_MULTIPLIER,
                1e-9,
            ),
            1.0,
        )

        weight = (
            0.45 * body_component
            + 0.35 * close_component
            + 0.20 * expansion_component
        )

        return float(min(max(weight, 0.0), 1.0))

    @staticmethod
    def wick_dominance(
        snapshot: TechnicalFeatureSnapshot,
    ) -> float:
        """
        Signed wick imbalance:
            +1 -> lower wick strongly dominates
            -1 -> upper wick strongly dominates
             0 -> balanced
        """

        total = (
            snapshot.upper_wick_ratio
            + snapshot.lower_wick_ratio
        )

        if total <= 0:
            return 0.0

        value = (
            snapshot.lower_wick_ratio
            - snapshot.upper_wick_ratio
        ) / total

        return float(min(max(value, -1.0), 1.0))

    @staticmethod
    def _true_ranges(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
    ) -> np.ndarray:
        if len(closes) == 1:
            return np.asarray(
                [highs[0] - lows[0]],
                dtype=np.float64,
            )

        previous_close = np.concatenate(
            ([closes[0]], closes[:-1])
        )

        return np.maximum.reduce(
            (
                highs - lows,
                np.abs(highs - previous_close),
                np.abs(lows - previous_close),
            )
        )

    @staticmethod
    def _rolling_mean_last(
        values: np.ndarray,
        period: int,
    ) -> float:
        if len(values) == 0:
            return 0.0

        window = values[-min(len(values), period):]
        return float(np.mean(window))

    @staticmethod
    def _ema_last(
        values: np.ndarray,
        period: int,
    ) -> float:
        if len(values) == 0:
            return 0.0

        alpha = 2.0 / (period + 1.0)
        ema = float(values[0])

        for value in values[1:]:
            ema = (
                alpha * float(value)
                + (1.0 - alpha) * ema
            )

        return float(ema)

    @staticmethod
    def _rsi_last(
        closes: np.ndarray,
        period: int,
    ) -> float:
        if len(closes) < 2:
            return 50.0

        deltas = np.diff(closes)

        gains = np.maximum(deltas, 0.0)
        losses = np.maximum(-deltas, 0.0)

        if len(deltas) <= period:
            average_gain = float(np.mean(gains))
            average_loss = float(np.mean(losses))
        else:
            average_gain = float(
                np.mean(gains[:period])
            )
            average_loss = float(
                np.mean(losses[:period])
            )

            for i in range(period, len(deltas)):
                average_gain = (
                    (average_gain * (period - 1))
                    + float(gains[i])
                ) / period

                average_loss = (
                    (average_loss * (period - 1))
                    + float(losses[i])
                ) / period

        if average_loss == 0:
            if average_gain == 0:
                return 50.0
            return 100.0

        rs = average_gain / average_loss
        return float(
            100.0 - (100.0 / (1.0 + rs))
        )

    @staticmethod
    def _momentum(
        closes: np.ndarray,
        lookback: int,
    ) -> float:
        if len(closes) <= lookback:
            return 0.0

        return float(
            closes[-1] - closes[-1 - lookback]
        )

    @staticmethod
    def _simple_return(
        closes: np.ndarray,
        lookback: int,
    ) -> float:
        if len(closes) <= lookback:
            return 0.0

        base = float(closes[-1 - lookback])

        if base == 0:
            return 0.0

        return float(
            (float(closes[-1]) / base) - 1.0
        )

    @staticmethod
    def _realized_volatility(
        closes: np.ndarray,
        lookback: int,
    ) -> float:
        if len(closes) < 2:
            return 0.0

        window = closes[
            -min(len(closes), lookback + 1):
        ]

        log_returns: list[float] = []

        for previous, current in zip(
            window[:-1],
            window[1:],
        ):
            previous = float(previous)
            current = float(current)

            if previous > 0 and current > 0:
                log_returns.append(
                    log(current / previous)
                )

        if len(log_returns) < 2:
            return 0.0

        return float(
            pstdev(log_returns)
        )

    @staticmethod
    def _zscore_last(
        closes: np.ndarray,
        lookback: int,
    ) -> float:
        if len(closes) < 2:
            return 0.0

        window = closes[
            -min(len(closes), lookback):
        ]

        mean = float(np.mean(window))
        std = float(np.std(window))

        if std <= 0:
            return 0.0

        return float(
            (float(closes[-1]) - mean) / std
        )

    @staticmethod
    def _efficiency_ratio(
        closes: np.ndarray,
        lookback: int,
    ) -> float:
        if len(closes) < 2:
            return 0.0

        window = closes[
            -min(len(closes), lookback + 1):
        ]

        if len(window) < 2:
            return 0.0

        displacement = abs(
            float(window[-1] - window[0])
        )

        path = float(
            np.sum(np.abs(np.diff(window)))
        )

        if path <= 0:
            return 0.0

        return float(
            min(max(displacement / path, 0.0), 1.0)
        )

    @staticmethod
    def _direction(
        open_price: float,
        close_price: float,
    ) -> int:
        if close_price > open_price:
            return 1
        if close_price < open_price:
            return -1
        return 0

    @staticmethod
    def _clip01(value: float) -> float:
        return min(max(float(value), 0.0), 1.0)

    @staticmethod
    def _normalize_activity(
        tick_activity: Optional[
            Sequence[float] | Iterable[float]
        ],
        required_length: int,
    ) -> list[float]:
        if tick_activity is None:
            return [1.0] * required_length

        activity = [
            max(float(value), 0.0)
            for value in tick_activity
        ]

        if len(activity) != required_length:
            raise ValueError(
                "tick_activity must have the same length as candles."
            )

        return activity

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
                    "All candles must use the same timeframe."
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
                    "Inconsistent candle high."
                )

            if candle.low > min(
                candle.open,
                candle.close,
                candle.high,
            ):
                raise ValueError(
                    "Inconsistent candle low."
                )

            if (
                previous_timestamp is not None
                and candle.timestamp <= previous_timestamp
            ):
                raise ValueError(
                    "Candles must be strictly chronological."
                )

            previous_timestamp = candle.timestamp
