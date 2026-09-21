
from dataclasses import dataclass


@dataclass
class SubscriberResult:
    target: str
    action: str
    status: str


class ConsoleSubscriber:

    def handle(self, event):

        return SubscriberResult(
            "CONSOLE",
            f"Display: {event.event_type}",
            "UPDATED"
        )


class AudioSubscriber:

    def handle(self, event):

        if event.level == "CRITICAL":
            action = "PLAY_CRITICAL_ALERT"
        else:
            action = "PLAY_INFO_ALERT"

        return SubscriberResult(
            "AUDIO",
            action,
            "TRIGGERED"
        )


class DatabaseSubscriber:

    def __init__(self):
        self.storage = []

    def handle(self, event):

        self.storage.append(event)

        return SubscriberResult(
            "DATABASE",
            "EVENT_SAVED",
            "STORED"
        )


class TraceSubscriber:

    def __init__(self):
        self.trace = []

    def handle(self, event):

        self.trace.append(
            event.event_type
        )

        return SubscriberResult(
            "TRACE",
            "TRACE_UPDATED",
            "RECORDED"
        )


class EventDispatcher:

    def __init__(self, subscribers):

        self.subscribers = subscribers


    def dispatch(self, event):

        return [
            subscriber.handle(event)
            for subscriber in self.subscribers
        ]
