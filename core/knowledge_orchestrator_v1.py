
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PipelineResult:
    pattern: str
    stage: str
    approved: bool
    confidence: float
    blockers: list = field(default_factory=list)
    trace: list = field(default_factory=list)


class KnowledgeOrchestrator:

    """
    End-to-end coordinator.

    Flow:
    Candle Analysis
        ->
    Hybrid Validation
        ->
    Knowledge Update
        ->
    Feedback
    """

    def run(
        self,
        pattern,
        hybrid_result,
        validation_result,
        knowledge_state=None
    ):

        trace = []

        trace.append("HYBRID_RECEIVED")

        if validation_result.state != "VALIDATED_HYBRID":
            return PipelineResult(
                pattern=pattern,
                stage="VALIDATION_BLOCK",
                approved=False,
                confidence=hybrid_result.confidence,
                blockers=validation_result.blockers,
                trace=trace
            )

        trace.append("VALIDATION_PASSED")

        if knowledge_state:
            knowledge_state.last_validation = datetime.now(
                timezone.utc
            ).isoformat()

            trace.append("KNOWLEDGE_UPDATED")

        return PipelineResult(
            pattern=pattern,
            stage="KNOWLEDGE_READY",
            approved=True,
            confidence=hybrid_result.confidence,
            blockers=[],
            trace=trace
        )
