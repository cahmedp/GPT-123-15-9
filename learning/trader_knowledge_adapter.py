
"""
Trader Knowledge Adapter

Safe bridge between Knowledge Registry and Virtual Traders.

Rules:
- ACTIVE_KNOWLEDGE only is exposed.
- PENDING/REJECTED never reach traders.
- Learning layer remains separated from live execution.
"""

from dataclasses import dataclass


@dataclass
class TraderKnowledge:
    trader: str
    knowledge_items: list
    count: int


class TraderKnowledgeAdapter:

    def __init__(self):
        self.allowed_state = "ACTIVE_KNOWLEDGE"


    def build_context(
        self,
        knowledge_items
    ):

        active = []

        for item in knowledge_items:

            if item.get("state") == self.allowed_state:
                active.append(item)


        return active


    def provide_to_trader(
        self,
        trader,
        knowledge_items
    ):

        active = self.build_context(
            knowledge_items
        )

        return TraderKnowledge(
            trader=trader,
            knowledge_items=active,
            count=len(active)
        )
