
"""
Counterfactual Learning Store

Records decisions that were NOT executed and evaluates
what would have happened later.

Purpose:
- reduce selection bias
- evaluate blocked/skipped opportunities
- learning layer only
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class CounterfactualEvent:
    candle_id: str
    decision_state: str
    reason: str
    future_result: str | None
    evaluated: bool
    timestamp: str


class CounterfactualStore:

    def __init__(self):
        self.events = []


    def record_no_trade(
        self,
        candle_id,
        reason
    ):

        event = CounterfactualEvent(
            candle_id=candle_id,
            decision_state="NO_TRADE",
            reason=reason,
            future_result=None,
            evaluated=False,
            timestamp=datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.events.append(event)

        return event


    def evaluate(
        self,
        candle_id,
        future_result
    ):

        for event in self.events:

            if event.candle_id == candle_id:

                event.future_result = future_result
                event.evaluated = True

                return event

        return None


    def all(self):
        return [
            asdict(event)
            for event in self.events
        ]
