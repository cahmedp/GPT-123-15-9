
"""
Market Health Guard

Protects the bot during poor market conditions.

Not a hard shutdown:
- Allows weak situations to be observed.
- Reduces confidence.
- Requests caution instead of blocking everything.

Examples:
- low volatility
- noisy movement
- unclear structure
"""

from dataclasses import dataclass


@dataclass
class MarketHealthResult:
    mode: str
    confidence_multiplier: float
    reason: str


class MarketHealthGuard:

    def evaluate(
        self,
        volatility,
        structure_quality,
        noise_score
    ):

        weakness = 0

        if volatility < 0.20:
            weakness += 1

        if structure_quality < 0.50:
            weakness += 1

        if noise_score > 0.70:
            weakness += 1


        if weakness >= 3:
            return MarketHealthResult(
                "DEFENSIVE",
                0.55,
                "Sterile market conditions"
            )

        if weakness == 2:
            return MarketHealthResult(
                "CAUTIOUS",
                0.75,
                "Reduced market quality"
            )


        return MarketHealthResult(
            "NORMAL",
            1.0,
            "Healthy conditions"
        )
