
"""
Lesson Lifecycle Test
"""

from learning.lesson_lifecycle import (
    LessonLifecycleManager
)


def run():

    manager = LessonLifecycleManager()


    print("\n================")
    print("PENDING")

    print(
        manager.evaluate(
            "break_retest",
            10,
            8
        )
    )


    print("\n================")
    print("ACTIVE")

    print(
        manager.evaluate(
            "break_retest",
            100,
            82
        )
    )


    print("\n================")
    print("RETIRED")

    print(
        manager.evaluate(
            "break_retest",
            100,
            30
        )
    )


if __name__ == "__main__":
    run()
