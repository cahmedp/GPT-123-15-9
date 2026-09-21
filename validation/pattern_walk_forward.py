
"""
Pattern Walk Forward Validator

Purpose:
Validate discovered patterns on unseen future blocks.

Flow:
Discovery period -> Future unseen period -> Evaluation

Prevents:
- overfitting
- memorizing historical noise
"""

from dataclasses import dataclass


@dataclass
class WalkForwardResult:
    pattern: str
    train_samples: int
    test_samples: int
    matches: int
    failures: int
    success_rate: float
    status: str


class PatternWalkForwardValidator:

    def validate(
        self,
        pattern,
        train_results,
        future_results
    ):

        test_samples = len(future_results)

        matches = future_results.count("MATCH")
        failures = future_results.count("FAILURE")

        effective = matches + failures

        rate = round(
            matches / effective,
            3
        ) if effective else 0


        if test_samples < 30:
            status = "INSUFFICIENT_FORWARD_DATA"

        elif rate >= 0.6:
            status = "FORWARD_VALIDATED"

        else:
            status = "FAILED_FORWARD_TEST"


        return WalkForwardResult(
            pattern=pattern,
            train_samples=len(train_results),
            test_samples=test_samples,
            matches=matches,
            failures=failures,
            success_rate=rate,
            status=status
        )
