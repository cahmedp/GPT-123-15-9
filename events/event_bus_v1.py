
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class SystemEvent:
    source: str
    event_type: str
    message: str
    level: str
    timestamp: str


class EventBus:

    def __init__(self):
        self.events = []

    def publish(
        self,
        source,
        event_type,
        message,
        level="INFO"
    ):

        event = SystemEvent(
            source=source,
            event_type=event_type,
            message=message,
            level=level,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        self.events.append(event)

        return event


    def latest(self, limit=10):
        return self.events[-limit:]
