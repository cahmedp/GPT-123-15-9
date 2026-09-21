"""
OTC Micro Cycle Intelligence Test

Purpose:
Detect the internal cycle of 30s OTC execution.

States:
- ACCUMULATION
- BREAKOUT_ATTEMPT
- EXPANSION
- EXHAUSTION
- CHOP

This layer observes only.
"""

from dataclasses import dataclass


@dataclass
class MicroCycleResult:
    state: str
    score: float
    reason: str


class OTCMicroCycleEngine:

    def analyze(
        self,
        compression: float,
        impulse: float,
        momentum: float,
        momentum_decay: float,
        noise: float,
        breakout_pressure: float,
    ) -> MicroCycleResult:

        if compression >= 0.70 and impulse < 0.40:
            return MicroCycleResult(
                "ACCUMULATION",
                round(compression, 3),
                "Compression before expansion"
            )

        if (
            compression >= 0.55
            and breakout_pressure >= 0.70
        ):
            return MicroCycleResult(
                "BREAKOUT_ATTEMPT",
                round(breakout_pressure, 3),
                "Pressure building near range boundary"
            )

        if (
            impulse >= 0.70
            and momentum >= 0.70
            and noise < 0.60
        ):
            return MicroCycleResult(
                "EXPANSION",
                round(impulse, 3),
                "Strong directional expansion"
            )

        if (
            momentum_decay >= 0.70
            or noise >= 0.85
        ):
            return MicroCycleResult(
                "EXHAUSTION",
                round(momentum_decay, 3),
                "Momentum deterioration detected"
            )

        return MicroCycleResult(
            "CHOP",
            round(1 - noise, 3),
            "No clean micro cycle"
        )


if __name__ == "__main__":

    engine = OTCMicroCycleEngine()

    cases = [
        (
            "Range accumulation",
            0.85, 0.25, 0.30, 0.20, 0.70, 0.40
        ),
        (
            "Fake breakout attempt",
            0.65, 0.35, 0.45, 0.25, 0.55, 0.80
        ),
        (
            "Real expansion",
            0.20, 0.85, 0.90, 0.10, 0.30, 0.90
        ),
        (
            "Exhaustion",
            0.30, 0.40, 0.35, 0.85, 0.80, 0.20
        ),
    ]

    for case in cases:
        print("\n================")
        print(case[0])
        print(engine.analyze(*case[1:]))
