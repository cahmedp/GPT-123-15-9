
from learning.bayesian_lesson_confidence import BayesianLessonConfidence

def run():

    manager = BayesianLessonConfidence()

    print("\n================")
    print("SMALL SAMPLE")
    print(manager.evaluate("break_retest", 5, 5))

    print("\n================")
    print("STRONG SAMPLE")
    print(manager.evaluate("break_retest", 100, 82))

    print("\n================")
    print("NEGATIVE SAMPLE")
    print(manager.evaluate("break_retest", 100, 20))


if __name__ == "__main__":
    run()
