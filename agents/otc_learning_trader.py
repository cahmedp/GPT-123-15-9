"""
OTC Learning Trader

Learns from outcomes.
Does not modify live strategy directly.
"""


class OTCLearningTrader:

    def __init__(self):
        self.lessons = []

    def learn(
        self,
        prediction: dict,
        outcome: dict
    ):

        lesson = {
            "prediction": prediction,
            "outcome": outcome,
        }

        self.lessons.append(lesson)

        return lesson

    def summary(self):

        return {
            "lessons_count": len(self.lessons)
        }
