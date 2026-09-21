
from events.event_bus_v1 import EventBus
from events.system_event_integrator_v1 import SystemEventIntegrator
from subscribers.event_subscribers_v1 import (
    ConsoleSubscriber,
    AudioSubscriber,
    DatabaseSubscriber,
    TraceSubscriber,
    EventDispatcher
)


def run():

    bus = EventBus()
    system = SystemEventIntegrator(bus)

    event = system.pattern_validated(
        "BULLISH_EXPANSION"
    )

    database = DatabaseSubscriber()
    trace = TraceSubscriber()

    dispatcher = EventDispatcher(
        [
            ConsoleSubscriber(),
            AudioSubscriber(),
            database,
            trace
        ]
    )

    print("\n================")
    print("EVENT SUBSCRIBERS")

    for result in dispatcher.dispatch(event):
        print(result)


if __name__ == "__main__":
    run()
