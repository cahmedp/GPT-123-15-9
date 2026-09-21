
"""
Weight Safety Guard

Protects learned trader weights from sudden unstable changes.

Rules:
- minimum samples before activation
- bounded weight movement
- prevents sudden jumps
- learning layer only
"""

from dataclasses import dataclass


@dataclass
class SafeWeightResult:
    previous: float
    proposed: float
    final_weight: float
    changed: bool
    reason: str


class WeightSafetyGuard:

    def __init__(
        self,
        min_samples=30,
        max_change=0.10,
    ):
        self.min_samples = min_samples
        self.max_change = max_change


    def apply(
        self,
        previous_weight,
        proposed_weight,
        samples
    ):

        if samples < self.min_samples:
            return SafeWeightResult(
                previous=previous_weight,
                proposed=proposed_weight,
                final_weight=previous_weight,
                changed=False,
                reason="Not enough samples"
            )


        difference = (
            proposed_weight -
            previous_weight
        )


        if abs(difference) > self.max_change:

            if difference > 0:
                final = previous_weight + self.max_change
            else:
                final = previous_weight - self.max_change

            return SafeWeightResult(
                previous=previous_weight,
                proposed=proposed_weight,
                final_weight=round(final, 3),
                changed=True,
                reason="Change limited by safety guard"
            )


        return SafeWeightResult(
            previous=previous_weight,
            proposed=proposed_weight,
            final_weight=round(proposed_weight, 3),
            changed=True,
            reason="Safe update"
        )
