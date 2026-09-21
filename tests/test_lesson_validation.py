
"""
Lesson Validation Test
"""

from learning.lesson_validation import (
    LessonValidator
)


def run():

    validator = LessonValidator(
        min_samples=30,
        activation_threshold=0.70
    )


    print("\n================")
    print("INSUFFICIENT DATA")


    print(
        validator.validate(
            samples=10,
            successes=9
        )
    )


    print("\n================")
    print("VALIDATED LESSON")


    print(
        validator.validate(
            samples=100,
            successes=82
        )
    )


    print("\n================")
    print("FAILED LESSON")


    print(
        validator.validate(
            samples=100,
            successes=45
        )
    )


if __name__ == "__main__":
    run()
