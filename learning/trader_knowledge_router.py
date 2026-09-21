
"""
Trader Knowledge Router

Routes ACTIVE knowledge only to the appropriate virtual trader.

Examples:
- Structure patterns -> STRUCTURE_TRADER
- Liquidity behavior -> LIQUIDITY_TRADER
- Evaluation/meta lessons -> LEARNING_TRADER

Does not execute decisions.
Learning distribution layer only.
"""

from dataclasses import dataclass


@dataclass
class RoutedKnowledge:
    trader: str
    items: list
    count: int


class TraderKnowledgeRouter:

    def __init__(self):
        self.allowed_state = "ACTIVE_KNOWLEDGE"


    def route(self, knowledge_items):

        result = {
            "STRUCTURE_TRADER": [],
            "LIQUIDITY_TRADER": [],
            "LEARNING_TRADER": []
        }

        for item in knowledge_items:

            if item.get("state") != self.allowed_state:
                continue

            target = item.get(
                "target",
                "LEARNING_TRADER"
            )

            if target in result:
                result[target].append(item)

        return result


    def get_for_trader(
        self,
        trader,
        knowledge_items
    ):

        routed = self.route(
            knowledge_items
        )

        items = routed.get(
            trader,
            []
        )

        return RoutedKnowledge(
            trader=trader,
            items=items,
            count=len(items)
        )
