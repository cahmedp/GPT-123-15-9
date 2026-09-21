
"""
Persistent Trader Memory abstraction.

Stores virtual trader lessons.
"""

import json
from pathlib import Path


class PersistentTraderMemory:

    def __init__(
        self,
        path="trader_memory.json"
    ):

        self.path = Path(path)
        self.records = []

        self.load()


    def store(self, lesson):

        self.records.append(
            lesson
        )

        self.save()


    def save(self):

        self.path.write_text(
            json.dumps(
                self.records,
                indent=2
            ),
            encoding="utf-8"
        )


    def load(self):

        if self.path.exists():

            self.records = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )


    def all(self):

        return list(self.records)
