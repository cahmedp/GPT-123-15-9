
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AuditEvent:
    timestamp: str
    source: str
    event_type: str
    message: str
    level: str


@dataclass
class AuditReport:
    total_events: int
    timeline: list
    critical_events: list
    pattern: str | None
    validation_found: bool
    summary: str


class EventReplayAudit:

    def __init__(self):
        self.events = []


    def record(self, event):

        self.events.append(
            AuditEvent(
                timestamp=event.timestamp,
                source=event.source,
                event_type=event.event_type,
                message=event.message,
                level=event.level
            )
        )


    def replay(self):

        critical = [
            e.event_type
            for e in self.events
            if e.level == "CRITICAL"
        ]

        pattern = None

        for e in self.events:
            if e.event_type == "PATTERN_VALIDATED":
                pattern = e.message.replace(
                    " validated",
                    ""
                )

        return AuditReport(
            total_events=len(self.events),
            timeline=[
                f"{e.timestamp} | {e.source} | {e.event_type}"
                for e in self.events
            ],
            critical_events=critical,
            pattern=pattern,
            validation_found=(
                "PATTERN_VALIDATED" in
                [e.event_type for e in self.events]
            ),
            summary="Replay completed successfully"
        )
