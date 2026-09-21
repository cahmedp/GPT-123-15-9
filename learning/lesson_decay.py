
"""
Lesson Decay

Detects weakening lessons.

Compares:
- historical performance
- recent performance
"""

from dataclasses import dataclass


@dataclass
class DecayResult:
    name: str
    status: str
    drop: float
    reason: str


class LessonDecayDetector:

    def check(
        self,
        name,
        historical_rate,
        recent_rate
    ):

        drop = round(
            historical_rate - recent_rate,
            3
        )

        if drop >= 0.20:
            return DecayResult(
                name,
                "DECAY_DETECTED",
                drop,
                "Recent performance degraded"
            )

        return DecayResult(
            name,
            "STABLE",
            drop,
            "No significant degradation"
        )
