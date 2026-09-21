
"""
Trader Consensus Engine

Combines virtual trader opinions.
Does not execute decisions.
"""

from dataclasses import dataclass


@dataclass
class ConsensusResult:
    state: str
    score: float
    votes: dict
    disagreements: list


class TraderConsensus:

    def evaluate(
        self,
        structure,
        liquidity,
        learning
    ):

        votes = {
            "structure": structure.view,
            "liquidity": liquidity.view,
            "learning": learning.get(
                "view",
                "NEUTRAL"
            )
        }

        disagreements = []

        if structure.view == "FOLLOW_STRUCTURE" and liquidity.view == "BLOCK":
            disagreements.append(
                "STRUCTURE_LIQUIDITY_CONFLICT"
            )

        positive = 0

        if structure.view == "FOLLOW_STRUCTURE":
            positive += 1

        if liquidity.view == "CLEAR":
            positive += 1

        if learning.get("view") in [
            "FOLLOW",
            "MATCH"
        ]:
            positive += 1

        score = round(
            positive / 3,
            3
        )

        state = (
            "ALIGNED"
            if score >= 0.66 and not disagreements
            else "CONFLICT"
        )

        return ConsensusResult(
            state=state,
            score=score,
            votes=votes,
            disagreements=disagreements
        )
