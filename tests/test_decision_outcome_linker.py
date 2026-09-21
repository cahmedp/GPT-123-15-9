
"""
Decision Outcome Linker Test
"""

from learning.decision_outcome_linker import (
    DecisionOutcomeLinker
)


def run():

    linker = DecisionOutcomeLinker()


    trace = {
        "candle_id":"NZDCAD_021230",
        "prediction":"CALL",
        "knowledge_used":[
            "break_retest"
        ],
        "regime":"EXPANSION"
    }


    print("\n================")
    print("MATCH OUTCOME")


    print(
        linker.create_lesson(
            trace,
            "CALL"
        )
    )


    print("\n================")
    print("FAILED OUTCOME")


    print(
        linker.create_lesson(
            trace,
            "PUT"
        )
    )


if __name__ == "__main__":
    run()
