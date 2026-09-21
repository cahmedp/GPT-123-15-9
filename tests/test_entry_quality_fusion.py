"""
Entry Quality Fusion Test

Combines:
- OTC Microstructure
- Strategy Competition result
- ADX
- ATR7
- Temporal Analysis

Testing layer only.
"""


from dataclasses import dataclass


@dataclass
class EntryQuality:
    quality: float
    state: str
    reason: str


class EntryQualityFusion:

    def evaluate(
        self,
        strategy_score: float,
        temporal_score: float,
        adx: float,
        atr_score: float,
        otc_impulse: float,
        otc_noise: float,
    ) -> EntryQuality:

        adx_score = (
            1.0 if adx >= 35 else
            0.85 if adx >= 25 else
            0.60 if adx >= 15 else
            0.30
        )

        quality = (
            0.30 * strategy_score
            + 0.25 * temporal_score
            + 0.15 * adx_score
            + 0.15 * atr_score
            + 0.15 * otc_impulse
        )

        quality *= (1 - 0.35 * otc_noise)

        if quality >= 0.80:
            return EntryQuality(
                round(quality, 3),
                "VALID_SETUP",
                "Strategy, timing and OTC behavior agree"
            )

        if quality >= 0.55:
            return EntryQuality(
                round(quality, 3),
                "WAIT_CONFIRMATION",
                "Setup exists but confirmation is incomplete"
            )

        return EntryQuality(
            round(quality, 3),
            "NO_EDGE",
            "Weak alignment"
        )


if __name__ == "__main__":

    engine = EntryQualityFusion()

    tests = [
        (
            "Fresh continuation",
            0.843,   # strategy
            0.878,   # temporal
            32,      # ADX
            0.8,     # ATR7 score
            0.764,   # OTC impulse
            0.288,   # OTC noise
        ),
        (
            "Late entry",
            0.843,
            0.558,
            32,
            0.8,
            0.764,
            0.288,
        ),
        (
            "Bad timing",
            0.843,
            0.190,
            18,
            0.4,
            0.30,
            0.90,
        ),
    ]

    for case in tests:
        print("\n====================")
        print(case[0])
        print(engine.evaluate(*case[1:]))