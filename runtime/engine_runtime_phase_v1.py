
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RuntimeConfig:
    version: str = "1.0 Experimental"
    mode: str = "ADVISORY_ONLY"
    execution_enabled: bool = False
    learning_enabled: bool = True


@dataclass
class RuntimeReport:
    version: str
    mode: str
    candles_processed: int
    patterns_detected: int
    validated: int
    blocked: int
    average_confidence: float
    knowledge_updates: int
    status: str


class EngineRuntime:

    def __init__(self):
        self.config = RuntimeConfig()
        self.candles = 0
        self.patterns = 0
        self.validated = 0
        self.blocked = 0
        self.confidences = []
        self.knowledge_updates = 0


    def process_cycle(self, confidence, validated=True):

        self.candles += 1
        self.patterns += 1
        self.confidences.append(confidence)

        if validated:
            self.validated += 1
        else:
            self.blocked += 1


    def update_knowledge(self):

        self.knowledge_updates += 1


    def report(self):

        avg = (
            round(
                sum(self.confidences) /
                len(self.confidences),
                3
            )
            if self.confidences else 0
        )

        return RuntimeReport(
            self.config.version,
            self.config.mode,
            self.candles,
            self.patterns,
            self.validated,
            self.blocked,
            avg,
            self.knowledge_updates,
            "STABLE"
        )
