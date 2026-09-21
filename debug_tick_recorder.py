import json
import time
from pathlib import Path


class TickRecorder:

    def __init__(self):
        self.file = Path("storage/debug_ticks.jsonl")
        self.file.parent.mkdir(
            exist_ok=True
        )

        self.counter = 0


    def record(self, tick):

        self.counter += 1

        data = {
            "counter": self.counter,
            "time": time.time(),

            "timestamp": tick.timestamp,
            "price": tick.price,
            "asset": tick.asset,
            "received_at": tick.received_at,
        }

        with self.file.open(
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                json.dumps(data)
                + "\n"
            )


        if self.counter % 100 == 0:
            print(
                f"[RECORDER] saved {self.counter} ticks"
            )