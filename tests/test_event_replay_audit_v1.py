
from events.event_bus_v1 import EventBus
from events.system_event_integrator_v1 import SystemEventIntegrator
from audit.event_replay_audit_v1 import EventReplayAudit


def run():

    bus = EventBus()
    system = SystemEventIntegrator(bus)

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

    audit = EventReplayAudit()

    for event in bus.latest():
        audit.record(event)

    report = audit.replay()

    print("\n================")
    print("AUDIT REPORT")

    print(report)


if __name__ == "__main__":
    run()
