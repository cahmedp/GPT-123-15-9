
"""
Consensus Confidence Test
"""

from agents.consensus_confidence import (
    ConsensusConfidenceAnalyzer
)


def run():

    analyzer = ConsensusConfidenceAnalyzer()


    print("\n================")
    print("FULL PARTICIPATION")


    print(
        analyzer.evaluate(
            score=0.9,
            active_votes={
                "STRUCTURE":"ALIGN",
                "LIQUIDITY":"ALIGN",
                "LEARNING":"ALIGN"
            },
            abstained=[],
            total_traders=3
        )
    )


    print("\n================")
    print("ABSTAIN CASE")


    print(
        analyzer.evaluate(
            score=0.8,
            active_votes={
                "STRUCTURE":"ALIGN",
                "LIQUIDITY":"ALIGN"
            },
            abstained=[
                "LEARNING"
            ],
            total_traders=3
        )
    )


if __name__ == "__main__":
    run()
