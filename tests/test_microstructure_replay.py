"""
Microstructure Replay Test
"""

from intelligence.microstructure_snapshot import create_snapshot
from intelligence.microstructure_memory import MicrostructureMemory
from intelligence.microstructure_replay import MicrostructureReplay


def run():

    snapshot = create_snapshot(
        "NZD/CAD",

        {
            "state":"EXPANSION",
            "impulse_strength":0.76,
            "noise_score":0.20,
            "momentum_score":0.90
        },

        {
            "state":"BREAK_RETEST"
        },

        {
            "state":"ACCEPTED_BREAKOUT"
        },

        {
            "state":"FRESH_EXECUTION"
        },

        {
            "state":"VALID_ENTRY",
            "evidence_score":0.86,
            "execution_score":0.86
        }
    )


    memory = MicrostructureMemory()

    sid = memory.store(snapshot)


    replay = MicrostructureReplay()


    print("\n================")
    print("SNAPSHOT")
    print(memory.get(sid))


    print("\n================")
    print("CONTINUATION RESULT")

    print(
        replay.validate(
            snapshot,
            {
                "direction":"CONTINUATION"
            }
        )
    )


    print("\n================")
    print("FAKE BREAKOUT RESULT")

    snapshot.pattern_state = "BREAKOUT"

    print(
        replay.validate(
            snapshot,
            {
                "returned_range":True
            }
        )
    )


if __name__ == "__main__":
    run()
