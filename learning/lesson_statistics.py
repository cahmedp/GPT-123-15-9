
"""
Lesson Statistics

Adds deeper evaluation for lessons:
- historical performance
- recent performance
- regime separation

Learning analysis only.
"""

from dataclasses import dataclass


@dataclass
class LessonStatistics:
    name: str
    total_samples: int
    total_matches: int
    historical_rate: float
    recent_rate: float
    regime_rates: dict


class LessonStatisticsAnalyzer:

    def analyze(
        self,
        name,
        history,
        recent_window=30
    ):

        total = len(history)
        matches = sum(
            1 for x in history
            if x["result"] == "MATCH"
        )

        recent = history[-recent_window:] \
            if len(history) >= recent_window \
            else history

        recent_matches = sum(
            1 for x in recent
            if x["result"] == "MATCH"
        )

        regimes = {}

        for item in history:

            regime = item.get(
                "regime",
                "UNKNOWN"
            )

            if regime not in regimes:
                regimes[regime] = {
                    "samples": 0,
                    "matches": 0
                }

            regimes[regime]["samples"] += 1

            if item["result"] == "MATCH":
                regimes[regime]["matches"] += 1


        regime_rates = {}

        for regime, data in regimes.items():
            regime_rates[regime] = round(
                data["matches"] / data["samples"],
                3
            )


        return LessonStatistics(
            name=name,
            total_samples=total,
            total_matches=matches,
            historical_rate=round(
                matches / total,
                3
            ) if total else 0,
            recent_rate=round(
                recent_matches / len(recent),
                3
            ) if recent else 0,
            regime_rates=regime_rates
        )
