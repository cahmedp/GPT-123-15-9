
"""
Market Health Memory
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class MarketHealthLesson:
    market_mode: str
    decision: str
    future_result: str
    lesson: str
    timestamp: str


class MarketHealthMemory:

    def evaluate(self, market_mode, decision, future_result):

        if market_mode == "DEFENSIVE" and decision == "NO_TRADE" and future_result == "LOSS_AVOIDED":
            lesson = "DEFENSIVE_MODE_PROTECTED_CAPITAL"

        elif market_mode == "DEFENSIVE" and decision == "NO_TRADE" and future_result == "WOULD_HAVE_WIN":
            lesson = "DEFENSIVE_MODE_TOO_STRICT"

        elif market_mode == "CAUTIOUS" and future_result == "MATCH":
            lesson = "CAUTIOUS_MODE_ACCEPTABLE"

        else:
            lesson = "NEUTRAL_OBSERVATION"

        return MarketHealthLesson(
            market_mode,
            decision,
            future_result,
            lesson,
            datetime.now(timezone.utc).isoformat()
        )
