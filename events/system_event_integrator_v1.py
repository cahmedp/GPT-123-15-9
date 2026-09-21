
class SystemEventIntegrator:

    def __init__(self, bus):
        self.bus = bus


    def agent_alignment(self, agent, state):

        return self.bus.publish(
            "AGENT",
            "AGENT_ALIGNMENT",
            f"{agent} -> {state}"
        )


    def pattern_validated(self, pattern):

        return self.bus.publish(
            "HYBRID",
            "PATTERN_VALIDATED",
            f"{pattern} validated",
            "CRITICAL"
        )


    def risk_block(self, reason):

        return self.bus.publish(
            "RISK",
            "RISK_BLOCK",
            reason,
            "WARNING"
        )


    def knowledge_updated(self, pattern):

        return self.bus.publish(
            "KNOWLEDGE",
            "KNOWLEDGE_UPDATED",
            f"{pattern} memory updated"
        )
