
"""
Lesson Validation Layer

Converts candidate lessons into validated knowledge.

Lifecycle:

PENDING
  |
  v
TESTING
  |
  v
ACTIVE

or

RETIRED
"""


from dataclasses import dataclass


@dataclass
class LessonValidationResult:
    state: str
    samples: int
    confidence: float
    reason: str


class LessonValidator:

    def __init__(
        self,
        min_samples=30,
        activation_threshold=0.70
    ):
        self.min_samples = min_samples
        self.activation_threshold = activation_threshold


    def validate(
        self,
        samples,
        successes
    ):

        if samples < self.min_samples:
            return LessonValidationResult(
                state="PENDING",
                samples=samples,
                confidence=0.0,
                reason="Not enough samples"
            )


        confidence = round(
            successes / samples,
            3
        )


        if confidence >= self.activation_threshold:

            return LessonValidationResult(
                state="ACTIVE",
                samples=samples,
                confidence=confidence,
                reason="Statistical threshold reached"
            )


        return LessonValidationResult(
            state="RETIRED",
            samples=samples,
            confidence=confidence,
            reason="Performance below threshold"
        )
