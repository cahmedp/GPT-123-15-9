"""
Performance tracking for virtual traders.
"""


class TraderPerformance:

    def __init__(self):
        self.stats = {}

    def update(
        self,
        trader,
        success: bool
    ):

        data = self.stats.setdefault(
            trader,
            {"wins":0, "losses":0}
        )

        if success:
            data["wins"] += 1
        else:
            data["losses"] += 1

        return data
