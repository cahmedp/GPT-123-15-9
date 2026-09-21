
"""
Decision Outcome Linker

Connects:
Decision Trace -> Real Outcome -> Evaluation -> Learning Lesson

Design principles:
- Raw decision history is immutable.
- Outcome evaluation is separated from prediction.
- Lessons are generated only after objective outcome exists.
- No live decision modification.
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class DecisionOutcomeLink:
    candle_id: str
    prediction: str
    outcome: str
    result: str
    lesson: dict
    timestamp: str


class DecisionOutcomeLinker:

    def evaluate_result(
        self,
        prediction,
        outcome
    ):

        if prediction == outcome:
            return "MATCH"

        return "MISMATCH"


    def create_lesson(
        self,
        trace,
        outcome
    ):

        result = self.evaluate_result(
            trace["prediction"],
            outcome
        )

        lesson = {
            "pattern": trace.get(
                "knowledge_used",
                []
            ),
            "regime": trace.get(
                "regime",
                "UNKNOWN"
            ),
            "result": result,
            "validated": True
            if result == "MATCH"
            else False
        }

        return DecisionOutcomeLink(
            candle_id=trace["candle_id"],
            prediction=trace["prediction"],
            outcome=outcome,
            result=result,
            lesson=lesson,
            timestamp=datetime.now(
                timezone.utc
            ).isoformat()
        )
