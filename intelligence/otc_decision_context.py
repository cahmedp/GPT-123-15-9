"""
OTC Decision Context

Single contract object that collects all validated evidence layers.
No prediction logic.
No BUY/SELL generation.
"""

from dataclasses import dataclass, field


@dataclass
class OTCDecisionContext:
    market_context: dict
    setup_context: dict
    micro_context: dict
    pattern_context: dict
    liquidity_context: dict
    temporal_context: dict
    candle_context: dict
    conflict_context: dict = field(default_factory=dict)

    def evidence_summary(self) -> dict:
        return {
            "market": self.market_context,
            "setup": self.setup_context,
            "micro": self.micro_context,
            "pattern": self.pattern_context,
            "liquidity": self.liquidity_context,
            "temporal": self.temporal_context,
            "candle": self.candle_context,
            "conflict": self.conflict_context,
        }

    def has_blocker(self) -> bool:
        blockers = [
            self.conflict_context.get("blocked", False),
            self.liquidity_context.get("blocked", False),
            self.candle_context.get("confirmed") is False,
        ]
        return any(blockers)
