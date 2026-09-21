
"""
Lesson Lifecycle Manager

Controls lesson maturity:

NEW -> PENDING -> ACTIVE -> RETIRED

Principles:
- One trade never creates a permanent lesson.
- Evidence accumulates over samples.
- Bad lessons can be retired.
- Learning does not directly modify live decisions.
"""

from dataclasses import dataclass


@dataclass
class LessonState:
    name: str
    state: str
    samples: int
    matches: int
    confidence: float
    reason: str


class LessonLifecycleManager:

    def __init__(
        self,
        min_samples=50,
        activation_confidence=0.75,
        retire_confidence=0.45
    ):
        self.min_samples = min_samples
        self.activation_confidence = activation_confidence
        self.retire_confidence = retire_confidence


    def evaluate(
        self,
        name,
        samples,
        matches
    ):

        confidence = round(
            matches / samples
            if samples
            else 0,
            3
        )


        if samples < self.min_samples:
            return LessonState(
                name,
                "PENDING",
                samples,
                matches,
                confidence,
                "Not enough evidence"
            )


        if confidence >= self.activation_confidence:
            return LessonState(
                name,
                "ACTIVE",
                samples,
                matches,
                confidence,
                "Evidence threshold reached"
            )


        if confidence < self.retire_confidence:
            return LessonState(
                name,
                "RETIRED",
                samples,
                matches,
                confidence,
                "Performance degraded"
            )


        return LessonState(
            name,
            "PENDING",
            samples,
            matches,
            confidence,
            "Needs more validation"
        )
