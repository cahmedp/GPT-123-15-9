
"""
Lesson Engine

Creates derived lessons from validated outcomes.

It does not modify live decisions.
"""

class LessonEngine:


    def derive(
        self,
        decision_event,
        outcome_event
    ):

        prediction = decision_event.payload
        outcome = outcome_event.payload


        matched = (
            prediction.get("direction")
            ==
            outcome.get("result")
        )


        return {
            "source_decision": prediction,
            "actual_outcome": outcome,
            "lesson_type":
                "CONFIRMED_PATTERN"
                if matched
                else
                "FAILED_PATTERN",
            "validated": True
        }
