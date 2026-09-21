"""
Microstructure Replay Validator

Compares decision-time snapshot
with the closed candle outcome.

No future leakage.
"""

from dataclasses import dataclass


@dataclass
class ReplayResult:

    outcome: str
    score: float
    reason: str


class MicrostructureReplay:

    def validate(
        self,
        snapshot,
        candle_result
    ):

        if (
            snapshot.micro_state == "EXPANSION"
            and candle_result.get("direction")
            == "CONTINUATION"
        ):
            return ReplayResult(
                "MATCH",
                0.90,
                "Expansion continued after snapshot"
            )


        if (
            snapshot.pattern_state == "BREAKOUT"
            and candle_result.get("returned_range")
        ):
            return ReplayResult(
                "FAKE_BREAKOUT",
                0.85,
                "Breakout failed after snapshot"
            )


        return ReplayResult(
            "UNKNOWN",
            0.50,
            "No strong historical match"
        )
