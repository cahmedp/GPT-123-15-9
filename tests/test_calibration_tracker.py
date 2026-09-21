
"""
Calibration Tracker Test
"""

from learning.calibration_tracker import (
    CalibrationTracker
)


def run():

    tracker = CalibrationTracker()


    print("\n================")
    print("GOOD CALIBRATION")


    for _ in range(8):
        tracker.add_result(
            confidence=0.80,
            success=True
        )

    for _ in range(2):
        tracker.add_result(
            confidence=0.80,
            success=False
        )

    print(
        tracker.evaluate()
    )


    print("\n================")
    print("BAD CALIBRATION")


    bad = CalibrationTracker()

    for _ in range(2):
        bad.add_result(
            confidence=0.90,
            success=True
        )

    for _ in range(8):
        bad.add_result(
            confidence=0.90,
            success=False
        )

    print(
        bad.evaluate()
    )


if __name__ == "__main__":
    run()
