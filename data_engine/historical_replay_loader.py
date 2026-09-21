
"""
Historical Replay Loader

Loads historical candle data and replays it
through analysis layers.

No execution logic.
"""

from dataclasses import dataclass


@dataclass
class ReplayWindow:
    candles: list
    size: int


class HistoricalReplayLoader:

    def __init__(self, window_size=10):
        self.window_size = window_size

    def create_windows(self, candles):

        windows = []

        for i in range(
            0,
            len(candles) - self.window_size + 1
        ):
            windows.append(
                ReplayWindow(
                    candles=candles[
                        i:i+self.window_size
                    ],
                    size=self.window_size
                )
            )

        return windows
