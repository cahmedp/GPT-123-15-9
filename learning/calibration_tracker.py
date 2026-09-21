
"""
Calibration Tracker

Measures whether confidence scores match real outcomes.

Goal:
confidence=0.80 should approximately represent
80% observed success over enough samples.

Observer only.
Does not change live decisions.
"""

from dataclasses import dataclass


@dataclass
class CalibrationResult:
    samples: int
    average_confidence: float
    actual_success_rate: float
    calibration_error: float
    status: str


class CalibrationTracker:

    def __init__(self):
        self.records = []


    def add_result(
        self,
        confidence: float,
        success: bool
    ):

        self.records.append(
            {
                "confidence": confidence,
                "success": success
            }
        )


    def evaluate(self):

        if not self.records:

            return CalibrationResult(
                samples=0,
                average_confidence=0,
                actual_success_rate=0,
                calibration_error=0,
                status="NO_DATA"
            )


        avg_confidence = sum(
            r["confidence"]
            for r in self.records
        ) / len(self.records)


        success_rate = sum(
            1
            for r in self.records
            if r["success"]
        ) / len(self.records)


        error = abs(
            avg_confidence - success_rate
        )


        if error <= 0.05:
            status = "WELL_CALIBRATED"

        elif error <= 0.15:
            status = "ACCEPTABLE"

        else:
            status = "MIS_CALIBRATED"


        return CalibrationResult(
            samples=len(self.records),
            average_confidence=round(avg_confidence,3),
            actual_success_rate=round(success_rate,3),
            calibration_error=round(error,3),
            status=status
        )
