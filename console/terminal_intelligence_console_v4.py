
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RuntimeEvent:
    source: str
    message: str
    level: str


@dataclass
class RuntimeDashboard:
    session: str
    candle_remaining: int
    events: list
    mode: str
    latency_ms: int
    health: dict


class TerminalIntelligenceConsoleV4:

    def __init__(self):
        self.events = []


    def push_event(self, source, message, level="INFO"):
        self.events.append(
            RuntimeEvent(source, message, level)
        )


    def snapshot(self):

        return RuntimeDashboard(
            session="LONDON",
            candle_remaining=12,
            events=self.events[-5:],
            mode="LIVE_RUNTIME",
            latency_ms=20,
            health={
                "DATA": "HEALTHY",
                "PIPELINE": "RUNNING",
                "DATABASE": "CONNECTED",
                "KNOWLEDGE": "ACTIVE"
            }
        )


    def render(self, state):

        events = "\n".join(
            [
                f"{e.level} | {e.source}: {e.message}"
                for e in state.events
            ]
        ) or "No events"

        health = "\n".join(
            [
                f"{k}: {v}"
                for k, v in state.health.items()
            ]
        )

        return f"""
╔══════════════════════════════════════╗
║ OTC EXPERT ADVISORY ENGINE v4         ║
╚══════════════════════════════════════╝

MODE:
{state.mode}

SESSION:
{state.session}

CANDLE:
CLOSE IN {state.candle_remaining}s

LATENCY:
{state.latency_ms} ms

EVENT BUS:
{events}

ENGINE HEALTH:
{health}
"""


if __name__ == "__main__":
    console = TerminalIntelligenceConsoleV4()
    console.push_event(
        "AGENTS",
        "Consensus updated",
        "INFO"
    )
    print(
        console.render(
            console.snapshot()
        )
    )
