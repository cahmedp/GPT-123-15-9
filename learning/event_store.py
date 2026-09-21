
"""
Event Store

Append-only storage for raw decision lifecycle events.

Principle:
Raw events are immutable.
Lessons are derived later.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass
class Event:
    event_type: str
    payload: dict
    timestamp: str


class EventStore:

    def __init__(self, path="otc_events.json"):
        self.path = Path(path)
        self.events = []
        self.load()


    def append(
        self,
        event_type,
        payload
    ):

        event = Event(
            event_type=event_type,
            payload=payload,
            timestamp=datetime.now(
                timezone.utc
            ).isoformat()
        )

        self.events.append(event)
        self.save()

        return event


    def save(self):

        self.path.write_text(
            json.dumps(
                [
                    asdict(e)
                    for e in self.events
                ],
                indent=2
            ),
            encoding="utf-8"
        )


    def load(self):

        if self.path.exists():

            data = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

            self.events = [
                Event(**item)
                for item in data
            ]


    def all(self):

        return list(self.events)
