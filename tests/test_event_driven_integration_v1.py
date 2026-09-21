
from events.event_bus_v1 import EventBus
from events.system_event_integrator_v1 import SystemEventIntegrator


def run():

    bus = EventBus()
    system = SystemEventIntegrator(bus)

    print("\n================")
    print("EVENT DRIVEN SYSTEM")

    system.agent_alignment(
        "STRUCTURE",
        "ALIGN"
    )

    system.pattern_validated(
        "BULLISH_EXPANSION"
    )

    system.knowledge_updated(
        "BULLISH_EXPANSION"
    )

    for event in bus.latest():
        print(event)


if __name__ == "__main__":
    run()
