
"""
Real Replay Evaluator

Validates a discovered pattern against future candles.

Rules:
- Pattern detection happens on past window only.
- Future candles are unseen evaluation data.
- Produces MATCH / FAILURE / AMBIGUOUS.
"""

from dataclasses import dataclass


@dataclass
class ReplayEvaluation:
    pattern: str
    result: str
    entry_close: float
    future_close: float
    movement: float


class RealReplayEvaluator:

    def evaluate(
        self,
        pattern,
        history_window,
        future_window
    ):

        if not history_window or not future_window:
            return ReplayEvaluation(
                pattern,
                "AMBIGUOUS",
                0,
                0,
                0
            )

        entry = history_window[-1]["close"]
        future = future_window[-1]["close"]

        movement = round(
            future - entry,
            3
        )

        if pattern == "BULLISH_EXPANSION":

            if movement > 0:
                result = "MATCH"
            elif movement < 0:
                result = "FAILURE"
            else:
                result = "AMBIGUOUS"

        elif pattern == "BEARISH_EXPANSION":

            if movement < 0:
                result = "MATCH"
            elif movement > 0:
                result = "FAILURE"
            else:
                result = "AMBIGUOUS"

        else:
            result = "AMBIGUOUS"


        return ReplayEvaluation(
            pattern,
            result,
            entry,
            future,
            movement
        )
