
"""
Regime Weight Manager

Adds market-regime awareness to trader reliability.

Weight is evaluated by:
- trader
- regime

Observer/learning layer only.
Does not change live decisions directly.
"""

from dataclasses import dataclass


@dataclass
class RegimeTraderWeight:
    trader: str
    regime: str
    weight: float
    samples: int


class RegimeWeightManager:

    def __init__(
        self,
        prior=0.5,
        prior_strength=10
    ):
        self.prior = prior
        self.prior_strength = prior_strength
        self.stats = {}


    def update(
        self,
        trader,
        regime,
        success
    ):

        key = (
            trader,
            regime
        )

        item = self.stats.setdefault(
            key,
            {
                "wins": 0,
                "losses": 0
            }
        )

        if success:
            item["wins"] += 1
        else:
            item["losses"] += 1


    def get_weight(
        self,
        trader,
        regime
    ):

        item = self.stats.get(
            (trader, regime),
            {
                "wins": 0,
                "losses": 0
            }
        )

        wins = item["wins"]
        losses = item["losses"]

        samples = wins + losses

        weight = (
            wins +
            self.prior * self.prior_strength
        ) / (
            samples +
            self.prior_strength
        )

        return RegimeTraderWeight(
            trader=trader,
            regime=regime,
            weight=round(weight, 3),
            samples=samples
        )
