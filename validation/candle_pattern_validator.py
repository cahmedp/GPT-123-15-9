
"""
Candle Pattern Validator

Validates patterns produced by Candle Intelligence Agents.

Checks:
- agent agreement
- historical evidence
- freshness
- sample confidence

Does not execute decisions.
"""

from dataclasses import dataclass


@dataclass
class PatternValidationResult:
    pattern: str
    trusted: bool
    confidence: float
    status: str
    reasons: list


class CandlePatternValidator:

    def validate(
        self,
        pattern,
        agent_reports,
        historical_occurrences,
        historical_successes,
        freshness_score
    ):

        reasons = []

        if not agent_reports:
            return PatternValidationResult(
                pattern,
                False,
                0.0,
                "NO_DATA",
                ["NO_AGENT_REPORTS"]
            )

        agreement = len(
            [
                r for r in agent_reports
                if r.pattern == pattern
            ]
        ) / len(agent_reports)


        if historical_occurrences < 30:
            reasons.append(
                "INSUFFICIENT_HISTORY"
            )

        if historical_occurrences:
            historical_rate = (
                historical_successes /
                historical_occurrences
            )
        else:
            historical_rate = 0


        sample_factor = min(
            historical_occurrences / 100,
            1.0
        )

        confidence = round(
            agreement
            * historical_rate
            * freshness_score
            * sample_factor,
            3
        )


        if agreement < 0.8:
            reasons.append(
                "LOW_AGENT_AGREEMENT"
            )

        if confidence >= 0.60 and not reasons:
            status = "TRUSTED_PATTERN"
            trusted = True
        else:
            status = "UNVERIFIED_PATTERN"
            trusted = False


        return PatternValidationResult(
            pattern,
            trusted,
            confidence,
            status,
            reasons
        )
