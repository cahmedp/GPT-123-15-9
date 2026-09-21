
from dataclasses import dataclass, field


@dataclass
class SimulationReport:
    total_candles: int
    windows_processed: int
    patterns_found: int
    approved_decisions: int
    blocked_decisions: int
    knowledge_updates: int
    average_confidence: float
    failures: list = field(default_factory=list)


class ProductionSimulationEngine:

    def __init__(
        self,
        pipeline,
        window_size=10
    ):
        self.pipeline = pipeline
        self.window_size = window_size


    def run(self, candles):

        windows = 0
        patterns = 0
        approved = 0
        blocked = 0
        confidence_sum = 0
        updates = 0
        failures = []

        for i in range(len(candles)):

            result = self.pipeline.process(
                candles[i]
            )

            if result.stage == "EXECUTION_READY":
                windows += 1
                patterns += 1
                approved += 1
                confidence_sum += result.confidence
                updates += 1

            elif result.stage == "RISK_BLOCK":
                blocked += 1
                failures.extend(
                    result.blockers
                )

        avg = round(
            confidence_sum / approved,
            3
        ) if approved else 0.0

        return SimulationReport(
            total_candles=len(candles),
            windows_processed=windows,
            patterns_found=patterns,
            approved_decisions=approved,
            blocked_decisions=blocked,
            knowledge_updates=updates,
            average_confidence=avg,
            failures=failures
        )
