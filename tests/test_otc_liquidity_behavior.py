"""
Liquidity Memory Book Test

Purpose:
Simulate liquidity behavior without real DOM.

Detect:
- Liquidity zones
- Sweep
- Breakout acceptance
- Fake breakout risk
"""

from dataclasses import dataclass


@dataclass
class LiquidityResult:
    state: str
    score: float
    reason: str


class LiquidityMemoryBook:

    def evaluate(
        self,
        zone_strength: float,
        previous_touches: int,
        breakout: bool,
        retest: bool,
        continuation: bool,
        rejection: float,
    ) -> LiquidityResult:

        if (
            breakout
            and not retest
            and rejection >= 0.70
        ):
            return LiquidityResult(
                "LIQUIDITY_SWEEP",
                0.80,
                "Breakout failed after liquidity grab"
            )

        if (
            breakout
            and retest
            and continuation
        ):
            score = (
                0.40 * zone_strength
                + 0.30 * min(previous_touches / 5, 1)
                + 0.30
            )

            return LiquidityResult(
                "ACCEPTED_BREAKOUT",
                round(score, 3),
                "Liquidity accepted after retest"
            )

        if zone_strength >= 0.70:
            return LiquidityResult(
                "LIQUIDITY_ZONE",
                round(zone_strength, 3),
                "Important historical liquidity area"
            )

        return LiquidityResult(
            "NO_CLEAR_LIQUIDITY",
            0.40,
            "No strong liquidity behavior"
        )


if __name__ == "__main__":

    engine = LiquidityMemoryBook()

    cases = [
        (
            "Real breakout with retest",
            0.85, 4, True, True, True, 0.10
        ),
        (
            "Fake breakout liquidity sweep",
            0.90, 5, True, False, False, 0.85
        ),
        (
            "Strong liquidity zone",
            0.80, 6, False, False, False, 0.20
        ),
        (
            "No liquidity",
            0.30, 1, False, False, False, 0.10
        ),
    ]

    for case in cases:
        print("\n================")
        print(case[0])
        print(engine.evaluate(*case[1:]))