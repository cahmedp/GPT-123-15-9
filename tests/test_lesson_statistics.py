
from learning.lesson_statistics import LessonStatisticsAnalyzer
from learning.lesson_decay import LessonDecayDetector


def run():

    history = [
        {"result":"MATCH","regime":"EXPANSION"},
        {"result":"MATCH","regime":"EXPANSION"},
        {"result":"MISMATCH","regime":"RANGE"},
        {"result":"MATCH","regime":"EXPANSION"},
    ]


    analyzer = LessonStatisticsAnalyzer()

    stats = analyzer.analyze(
        "break_retest",
        history
    )

    print("\n================")
    print("STATISTICS")
    print(stats)


    decay = LessonDecayDetector()

    print("\n================")
    print("DECAY CHECK")

    print(
        decay.check(
            "break_retest",
            0.82,
            0.55
        )
    )


if __name__ == "__main__":
    run()
