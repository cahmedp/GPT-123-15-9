
"""
Opinion Normalizer

Converts different trader expressions into a shared semantic language.

The consensus layer should compare meaning, not raw strings.
"""

from dataclasses import dataclass


@dataclass
class NormalizedOpinion:
    trader: str
    raw: str
    normalized: str


class OpinionNormalizer:

    POSITIVE = {
        "FOLLOW_STRUCTURE",
        "CLEAR",
        "MATCH",
        "VALID",
        "BULLISH_ALIGNMENT",
        "BREAKOUT_ACCEPTED"
    }

    NEGATIVE = {
        "WAIT",
        "FAILURE",
        "BLOCKED",
        "LIQUIDITY_SWEEP",
        "CONFLICT",
        "INVALID"
    }


    def normalize(
        self,
        trader,
        opinion
    ):

        if opinion in self.POSITIVE:
            state = "ALIGN"

        elif opinion in self.NEGATIVE:
            state = "BLOCK"

        else:
            state = "UNKNOWN"


        return NormalizedOpinion(
            trader=trader,
            raw=opinion,
            normalized=state
        )
