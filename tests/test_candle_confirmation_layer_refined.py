"""
Refined Candle Confirmation Layer Test

Adds:
- Wick rejection detection
- Weak close rejection
- Doji uncertainty
- Strong continuation close
"""

from dataclasses import dataclass


@dataclass
class CandleConfirmationResult:
    state: str
    score: float
    reason: str


class CandleConfirmationLayer:

    def evaluate(
        self,
        entry_quality: float,
        candle_closed: bool,
        body_strength: float,
        close_position: float,
        wick_rejection: float,
    ) -> CandleConfirmationResult:

        if not candle_closed:
            return CandleConfirmationResult(
                "WAIT_CONFIRMATION",
                round(entry_quality, 3),
                "Waiting for candle close confirmation",
            )

        # Rejection candle:
        # strong wick + weak close means failed confirmation
        if (
            wick_rejection >= 0.70
            and close_position < 0.50
        ):
            return CandleConfirmationResult(
                "REJECT",
                round(entry_quality * 0.5, 3),
                "Wick rejection invalidated the setup",
            )

        confirmation_score = (
            0.45 * body_strength
            + 0.35 * close_position
            + 0.20 * (1 - wick_rejection)
        )

        final_score = (
            0.65 * entry_quality
            + 0.35 * confirmation_score
        )

        if final_score >= 0.80:
            return CandleConfirmationResult(
                "VALID_ENTRY",
                round(final_score, 3),
                "Strong close confirmation",
            )

        if final_score >= 0.60:
            return CandleConfirmationResult(
                "WAIT_CONFIRMATION",
                round(final_score, 3),
                "Close confirmation is incomplete",
            )

        return CandleConfirmationResult(
            "REJECT",
            round(final_score, 3),
            "Candle structure failed",
        )


if __name__ == "__main__":

    engine = CandleConfirmationLayer()

    tests = [
        (
            "Strong continuation",
            0.84, True, 0.85, 0.90, 0.10
        ),
        (
            "Waiting close",
            0.84, False, 0.85, 0.90, 0.10
        ),
        (
            "Wick rejection",
            0.84, True, 0.35, 0.40, 0.80
        ),
        (
            "Doji uncertainty",
            0.70, True, 0.20, 0.50, 0.40
        ),
    ]

    for case in tests:
        print("\n================")
        print(case[0])
        print(
            engine.evaluate(*case[1:])
        )
