
"""
Fault Injection Utilities

Used to test system resilience.

Simulates:
- trader failure
- memory failure
- data degradation
- risk blocking

Testing only.
Does not modify production decisions.
"""

from dataclasses import dataclass


@dataclass
class FaultResult:
    component: str
    status: str
    fallback: str


class FaultInjector:

    def simulate(self, component):

        fallbacks = {
            "TRADER_FAILURE": "REMOVE_VOTE_USE_REMAINING_TRADERS",
            "MEMORY_FAILURE": "CONTINUE_WITHOUT_LEARNING",
            "DATA_DEGRADED": "REDUCE_CONFIDENCE",
            "RISK_BLOCK": "STOP_DECISION",
        }

        return FaultResult(
            component=component,
            status="INJECTED",
            fallback=fallbacks.get(
                component,
                "UNKNOWN"
            )
        )
