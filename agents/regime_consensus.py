
"""
Regime Consensus V3

Supports:
ALIGN
BLOCK
ABSTAIN

ABSTAIN does not count as disagreement.
"""

from dataclasses import dataclass


@dataclass
class ConsensusResult:
    state: str
    score: float
    active_votes: dict
    abstained: list
    conflicts: list


class RegimeConsensus:

    def evaluate(
        self,
        opinions,
        weights
    ):

        score_total = 0
        weight_total = 0

        active_votes = {}
        abstained = []
        conflicts = []


        for trader, data in opinions.items():

            state = data["state"]
            weight = weights.get(
                trader,
                0.5
            )

            if state == "ABSTAIN":
                abstained.append(trader)
                continue


            active_votes[trader] = {
                "state": state,
                "weight": weight
            }

            weight_total += weight

            if state == "ALIGN":
                score_total += weight


        score = round(
            score_total / weight_total
            if weight_total
            else 0,
            3
        )


        states = {
            x["state"]
            for x in active_votes.values()
        }

        if "ALIGN" in states and "BLOCK" in states:
            conflicts.append(
                "TRADER_DISAGREEMENT"
            )


        return ConsensusResult(
            state=(
                "ALIGNED"
                if score >= 0.65 and not conflicts
                else "CONFLICT"
            ),
            score=score,
            active_votes=active_votes,
            abstained=abstained,
            conflicts=conflicts
        )
