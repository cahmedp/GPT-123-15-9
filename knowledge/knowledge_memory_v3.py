
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib


@dataclass
class KnowledgeMemory:
    name: str
    version: int
    pattern_hash: str
    regime: str
    timeframe_signature: str
    state: str
    confidence: float
    evidence: dict = field(default_factory=dict)
    history: list = field(default_factory=list)
    retirement_reason: str | None = None


class KnowledgeMemoryManager:

    def create(
        self,
        name,
        regime,
        timeframe_signature,
        confidence
    ):

        raw = f"{name}:{regime}:{timeframe_signature}"

        pattern_hash = hashlib.sha256(
            raw.encode()
        ).hexdigest()[:12]

        return KnowledgeMemory(
            name=name,
            version=1,
            pattern_hash=pattern_hash,
            regime=regime,
            timeframe_signature=timeframe_signature,
            state="ACTIVE_KNOWLEDGE",
            confidence=confidence
        )


    def add_evidence(
        self,
        memory,
        evidence_type,
        data
    ):
        memory.evidence[evidence_type] = data
        return memory


    def evolve_version(
        self,
        memory,
        reason
    ):
        memory.version += 1

        memory.history.append({
            "version": memory.version,
            "reason": reason,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat()
        })

        return memory


    def resurrect(
        self,
        memory
    ):
        memory.state = "ACTIVE_KNOWLEDGE"
        memory.retirement_reason = None
        return memory
