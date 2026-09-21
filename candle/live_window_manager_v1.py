
from collections import deque


class CandleWindowManager:

    def __init__(self, size=10):
        self.window = deque(maxlen=size)


    def add(self, candle):

        self.window.append(candle)

        return {
            "ready": len(self.window) == self.window.maxlen,
            "size": len(self.window),
            "candles": list(self.window)
        }


    def reset(self):
        self.window.clear()
