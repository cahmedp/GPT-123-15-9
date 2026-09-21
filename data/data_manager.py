from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict
from threading import RLock
from typing import Iterable, Optional

from config import CONFIG
from data.pocket_connector import HistoricalCandle, MarketTick


class DataManager:
    """
    Central data layer.

    Storage contract:
    - ticks are kept as a runtime stream buffer.
    - candles are isolated by (asset, timeframe).
    - analysis consumers never receive mixed-asset sequences.
    """

    def __init__(self) -> None:
        self._ticks = deque(maxlen=CONFIG.TICK_QUEUE_MAXSIZE)

        self._candles: dict[tuple[str, int], deque[HistoricalCandle]] = defaultdict(
            lambda: deque(maxlen=CONFIG.MAX_CANDLES_IN_MEMORY)
        )

        self._lock = RLock()

    def add_tick(self, tick: MarketTick) -> None:
        with self._lock:
            self._ticks.append(tick)

    def _candle_key(self, candle: HistoricalCandle) -> tuple[str, int]:
        return (
            str(candle.asset),
            int(candle.timeframe_seconds),
        )

    def add_candle(self, candle: HistoricalCandle) -> None:
        with self._lock:
            self._candles[self._candle_key(candle)].append(candle)

    def add_candles(
        self,
        candles: Iterable[HistoricalCandle],
    ) -> None:
        with self._lock:
            for candle in candles:
                self._candles[self._candle_key(candle)].append(candle)

    def latest_ticks(self, count: Optional[int] = None) -> list[MarketTick]:
        with self._lock:
            data = list(self._ticks)

        return data if count is None else data[-count:]

    def latest_candles(
        self,
        count: Optional[int] = None,
    ) -> list[HistoricalCandle]:
        with self._lock:
            data: list[HistoricalCandle] = []
            for bucket in self._candles.values():
                data.extend(bucket)

        data.sort(key=lambda candle: candle.timestamp)
        return data if count is None else data[-count:]

    def candles_for(
        self,
        asset: str,
        timeframe_seconds: int,
        count: Optional[int] = None,
    ) -> list[HistoricalCandle]:
        key = (str(asset), int(timeframe_seconds))
        with self._lock:
            data = list(self._candles.get(key, ()))

        data.sort(key=lambda candle: candle.timestamp)
        return data if count is None else data[-count:]

    def candle_count(self) -> int:
        with self._lock:
            return sum(len(bucket) for bucket in self._candles.values())

    def tick_count(self) -> int:
        with self._lock:
            return len(self._ticks)

    def clear(self) -> None:
        with self._lock:
            self._ticks.clear()
            self._candles.clear()

    def export_state(self) -> dict:
        with self._lock:
            candles = [
                asdict(candle)
                for bucket in self._candles.values()
                for candle in bucket
            ]

            return {
                "ticks": [asdict(tick) for tick in self._ticks],
                "candles": candles,
                "tick_count": len(self._ticks),
                "candle_count": len(candles),
            }

    def ready_for_analysis(self) -> bool:
        return self.candle_count() >= CONFIG.MIN_BASE_CANDLES
