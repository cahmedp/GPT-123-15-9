
"""
Event Sourcing Learning Test
"""

from learning.event_store import EventStore
from learning.lesson_engine import LessonEngine


def run():

    store = EventStore(
        "test_events.json"
    )


    print("\n================")
    print("STORE EVENTS")


    decision = store.append(
        "DECISION_EVENT",
        {
            "candle_id":"NZDCAD_021230",
            "direction":"CALL",
            "confidence":0.86
        }
    )


    outcome = store.append(
        "OUTCOME_EVENT",
        {
            "candle_id":"NZDCAD_021230",
            "result":"CALL"
        }
    )


    print(decision)
    print(outcome)


    print("\n================")
    print("DERIVED LESSON")


    lesson = LessonEngine().derive(
        decision,
        outcome
    )

    print(lesson)


if __name__ == "__main__":
    run()
