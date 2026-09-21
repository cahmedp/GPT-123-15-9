from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from config import CONFIG
from data.pocket_connector import HistoricalCandle, MarketTick


@dataclass(slots=True)
class _WorkingCandle:
    bucket_start: float
    open: float
    high: float
    low: float
    close: float
    asset: str
    timeframe_seconds: int

    def update(self, price: float) -> None:
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price

    def to_closed(self) -> HistoricalCandle:
        return HistoricalCandle(
            timestamp=self.bucket_start,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            asset=self.asset,
            timeframe_seconds=self.timeframe_seconds,
        )


class CandleBuilder:
    """
    Builds fully closed OHLC candles from live Pocket Option ticks.

    Final supported timeframes:
        - 30 seconds: trigger timeframe
        - 1 minute: setup timeframe
        - 5 minutes: context timeframe

    Important design rules:
        - Uses market/event timestamps, not local arrival time.
        - Emits only CLOSED candles.
        - Does not invent missing candles.
        - Does not use future ticks to modify an already closed candle.
        - Can be seeded with historical 30-second candles before live streaming.
    """

    def __init__(
        self,
        timeframes: Optional[Iterable[int]] = None,
    ) -> None:
        configured = tuple(
            sorted(
                set(
                    timeframes
                    or (
                        CONFIG.BASE_TIMEFRAME_SECONDS,
                        CONFIG.TIMEFRAME_1M_SECONDS,
                        CONFIG.TIMEFRAME_5M_SECONDS,
                    )
                )
            )
        )

        if not configured:
            raise ValueError("At least one timeframe is required.")

        if any(int(tf) <= 0 for tf in configured):
            raise ValueError("All timeframes must be positive integers.")

        self._timeframes = tuple(int(tf) for tf in configured)

        self._working: Dict[int, Optional[_WorkingCandle]] = {
            tf: None for tf in self._timeframes
        }

        self._last_closed_start: Dict[int, Optional[float]] = {
            tf: None for tf in self._timeframes
        }

        self._last_tick_timestamp: Optional[float] = None
        self._last_tick_price: Optional[float] = None

    @property
    def timeframes(self) -> tuple[int, ...]:
        return self._timeframes

    def add_tick(
        self,
        tick: MarketTick,
    ) -> Dict[int, List[HistoricalCandle]]:
        """
        Process one live market tick.

        Returns:
            {
                30: [closed_candle_if_any],
                60: [closed_candle_if_any],
                300: [closed_candle_if_any],
            }

        Usually each list is empty or contains one candle.
        """

        self._validate_tick(tick)

        # Ignore an exact duplicate tick.
        if (
            self._last_tick_timestamp is not None
            and tick.timestamp == self._last_tick_timestamp
            and tick.price == self._last_tick_price
        ):
            return {tf: [] for tf in self._timeframes}

        # Old/out-of-order ticks are deliberately rejected.
        # Updating historical buckets after they have closed would introduce
        # inconsistent state into live reasoning.
        if (
            self._last_tick_timestamp is not None
            and tick.timestamp < self._last_tick_timestamp
        ):
            return {tf: [] for tf in self._timeframes}

        self._last_tick_timestamp = tick.timestamp
        self._last_tick_price = tick.price

        closed: Dict[int, List[HistoricalCandle]] = {
            tf: [] for tf in self._timeframes
        }

        for timeframe in self._timeframes:
            finished = self._process_price(
                timestamp=tick.timestamp,
                price=tick.price,
                asset=tick.asset,
                timeframe=timeframe,
            )

            if finished is not None:
                closed[timeframe].append(finished)

        return closed

    def seed_base_candles(
        self,
        candles: Iterable[HistoricalCandle],
    ) -> Dict[int, List[HistoricalCandle]]:
        """
        Seed the builder from historical BASE timeframe candles.

        This is used once at startup before live ticks arrive.

        Higher timeframes are reconstructed from the historical 30-second OHLC
        candles while preserving chronological order and avoiding future
        leakage.

        The latest higher-timeframe bucket remains open until enough later
        market data proves that it is closed.
        """

        base_tf = CONFIG.BASE_TIMEFRAME_SECONDS

        ordered = sorted(
            list(candles),
            key=lambda candle: candle.timestamp,
        )

        for candle in ordered:
            if candle.timeframe_seconds != base_tf:
                raise ValueError(
                    f"seed_base_candles expects {base_tf}s candles only."
                )
            self._validate_candle(candle)

        emitted: Dict[int, List[HistoricalCandle]] = {
            tf: [] for tf in self._timeframes
        }

        if not ordered:
            return emitted

        # Seed base timeframe as already-closed history.
        if base_tf in self._timeframes:
            emitted[base_tf].extend(ordered)
            self._last_closed_start[base_tf] = ordered[-1].timestamp

        # Build higher timeframes from the base candles.
        for timeframe in self._timeframes:
            if timeframe == base_tf:
                continue

            for candle in ordered:
                finished = self._process_ohlc_candle(
                    candle=candle,
                    target_timeframe=timeframe,
                )

                if finished is not None:
                    emitted[timeframe].append(finished)

        last = ordered[-1]
        self._last_tick_timestamp = (
            last.timestamp + float(last.timeframe_seconds)
        )
        self._last_tick_price = last.close

        return emitted

    def current_candle(
        self,
        timeframe: int,
    ) -> Optional[HistoricalCandle]:
        """
        Return a snapshot of the currently-forming candle.

        This snapshot is for UI/diagnostics only.
        Decision engines should use closed candles.
        """

        if timeframe not in self._working:
            raise KeyError(f"Unsupported timeframe: {timeframe}")

        working = self._working[timeframe]

        if working is None:
            return None

        return HistoricalCandle(
            timestamp=working.bucket_start,
            open=working.open,
            high=working.high,
            low=working.low,
            close=working.close,
            asset=working.asset,
            timeframe_seconds=working.timeframe_seconds,
        )

    def reset(self) -> None:
        for timeframe in self._timeframes:
            self._working[timeframe] = None
            self._last_closed_start[timeframe] = None

        self._last_tick_timestamp = None
        self._last_tick_price = None

    def _process_price(
        self,
        timestamp: float,
        price: float,
        asset: str,
        timeframe: int,
    ) -> Optional[HistoricalCandle]:

        bucket = self._bucket_start(
            timestamp=timestamp,
            timeframe=timeframe,
        )

        current = self._working[timeframe]

        if current is None:
            self._working[timeframe] = _WorkingCandle(
                bucket_start=bucket,
                open=price,
                high=price,
                low=price,
                close=price,
                asset=asset,
                timeframe_seconds=timeframe,
            )
            return None

        if bucket == current.bucket_start:
            current.update(price)
            return None

        if bucket < current.bucket_start:
            return None

        closed = current.to_closed()

        self._working[timeframe] = _WorkingCandle(
            bucket_start=bucket,
            open=price,
            high=price,
            low=price,
            close=price,
            asset=asset,
            timeframe_seconds=timeframe,
        )

        return self._accept_closed(
            timeframe=timeframe,
            candle=closed,
        )

    def _process_ohlc_candle(
        self,
        candle: HistoricalCandle,
        target_timeframe: int,
    ) -> Optional[HistoricalCandle]:

        bucket = self._bucket_start(
            timestamp=candle.timestamp,
            timeframe=target_timeframe,
        )

        current = self._working[target_timeframe]

        if current is None:
            self._working[target_timeframe] = _WorkingCandle(
                bucket_start=bucket,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                asset=candle.asset,
                timeframe_seconds=target_timeframe,
            )
            return None

        if bucket == current.bucket_start:
            current.high = max(current.high, candle.high)
            current.low = min(current.low, candle.low)
            current.close = candle.close
            return None

        if bucket < current.bucket_start:
            return None

        closed = current.to_closed()

        self._working[target_timeframe] = _WorkingCandle(
            bucket_start=bucket,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            asset=candle.asset,
            timeframe_seconds=target_timeframe,
        )

        return self._accept_closed(
            timeframe=target_timeframe,
            candle=closed,
        )

    def _accept_closed(
        self,
        timeframe: int,
        candle: HistoricalCandle,
    ) -> Optional[HistoricalCandle]:

        last_start = self._last_closed_start[timeframe]

        if (
            last_start is not None
            and candle.timestamp <= last_start
        ):
            return None

        self._last_closed_start[timeframe] = candle.timestamp
        return candle

    @staticmethod
    def _bucket_start(
        timestamp: float,
        timeframe: int,
    ) -> float:
        return float(
            int(timestamp // timeframe) * timeframe
        )

    @staticmethod
    def _validate_tick(tick: MarketTick) -> None:
        if tick.timestamp <= 0:
            raise ValueError("Tick timestamp must be positive.")

        if tick.price <= 0:
            raise ValueError("Tick price must be positive.")

        if not tick.asset:
            raise ValueError("Tick asset cannot be empty.")

    @staticmethod
    def _validate_candle(
        candle: HistoricalCandle,
    ) -> None:

        if candle.timestamp <= 0:
            raise ValueError("Candle timestamp must be positive.")

        if candle.timeframe_seconds <= 0:
            raise ValueError(
                "Candle timeframe must be positive."
            )

        if min(
            candle.open,
            candle.high,
            candle.low,
            candle.close,
        ) <= 0:
            raise ValueError(
                "Candle contains non-positive prices."
            )

        if candle.high < max(
            candle.open,
            candle.close,
            candle.low,
        ):
            raise ValueError(
                "Candle high is inconsistent."
            )

        if candle.low > min(
            candle.open,
            candle.close,
            candle.high,
        ):
            raise ValueError(
                "Candle low is inconsistent."
            )
