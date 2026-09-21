
"""
Bayesian Weight Manager

Purpose:
Estimate trader reliability without overreacting to small samples.

Features:
- Prior belief prevents small sample explosion
- Returns bounded reliability
- Tracks wins/losses
- Observer/learning layer only
"""


from dataclasses import dataclass


@dataclass
class TraderWeight:
    trader: str
    weight: float
    samples: int


class BayesianWeightManager:

    def __init__(
        self,
        prior_success=0.5,
        prior_strength=10
    ):
        self.prior_success = prior_success
        self.prior_strength = prior_strength
        self.data = {}


    def update(
        self,
        trader,
        success
    ):

        stats = self.data.setdefault(
            trader,
            {
                "wins": 0,
                "losses": 0
            }
        )

        if success:
            stats["wins"] += 1
        else:
            stats["losses"] += 1


    def get_weight(
        self,
        trader
    ):

        stats = self.data.get(
            trader,
            {
                "wins":0,
                "losses":0
            }
        )

        wins = stats["wins"]
        losses = stats["losses"]

        samples = wins + losses


        posterior = (
            wins +
            self.prior_success *
            self.prior_strength
        ) / (
            samples +
            self.prior_strength
        )


        return TraderWeight(
            trader=trader,
            weight=round(
                posterior,
                3
            ),
            samples=samples
        )
