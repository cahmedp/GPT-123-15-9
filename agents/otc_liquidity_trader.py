"""
OTC Liquidity Trader

Looks for invalidation behavior:
fake breaks, sweeps, noise.
"""


from dataclasses import dataclass


@dataclass
class LiquidityOpinion:
    trader: str
    view: str
    confidence: float
    warnings: list


class OTCLiquidityTrader:

    def analyze(self, snapshot: dict) -> LiquidityOpinion:

        warnings = []

        liquidity = snapshot.get(
            "liquidity_state",
            ""
        )

        if liquidity == "LIQUIDITY_SWEEP":
            warnings.append(
                "Possible liquidity failure"
            )

        if snapshot.get("noise_score", 0) > 0.7:
            warnings.append(
                "High market noise"
            )

        blocked = len(warnings) > 0

        return LiquidityOpinion(
            trader="LIQUIDITY_TRADER",
            view="BLOCK" if blocked else "CLEAR",
            confidence=round(
                0.8 if blocked else 0.85,
                3
            ),
            warnings=warnings,
        )
