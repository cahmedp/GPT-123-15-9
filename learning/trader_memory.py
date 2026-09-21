"""
Persistent memory abstraction.
"""


class TraderMemory:

    def __init__(self):
        self.records = []

    def store(self, item):
        self.records.append(item)

    def all(self):
        return list(self.records)
