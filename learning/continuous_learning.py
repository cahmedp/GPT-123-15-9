from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

from config import CONFIG
from memory.knowledge_base import KnowledgeBase, KnowledgeItem
from memory.memory_manager import MemoryCase, MemoryManager
from memory.trade_journal import TradeJournal


@dataclass(frozen=True, slots=True)
class LearningCandidate:
    """
    A statistically observed lesson that may be promoted to KnowledgeBase.

    It is only a proposal until validation requirements are satisfied.
    """

    key: str
    category: str
    title: str
    description: str

    direction: str
    regime: Optional[str]

    observations: int
    successes: int
    failures: int

    success_rate: float
    confidence: float
    reliability: float

    tags: tuple[str, ...] = field(default_factory=tuple)
    evidence: Mapping[str, Any] = field(default_factory=dict)

    @property
    def resolved(self) -> int:
        return self.successes + self.failures

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "direction": self.direction,
            "regime": self.regime,
            "observations": self.observations,
            "successes": self.successes,
            "failures": self.failures,
            "resolved": self.resolved,
            "success_rate": self.success_rate,
            "confidence": self.confidence,
            "reliability": self.reliability,
            "tags": list(self.tags),
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class LearningReport:
    generated_at: float

    resolved_cases_scanned: int
    candidates_found: int
    candidates_promoted: int
    knowledge_updated: int

    defensive_mode: bool
    consecutive_bad_outcomes: int

    candidate_summaries: tuple[LearningCandidate, ...] = field(
        default_factory=tuple
    )
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "resolved_cases_scanned": self.resolved_cases_scanned,
            "candidates_found": self.candidates_found,
            "candidates_promoted": self.candidates_promoted,
            "knowledge_updated": self.knowledge_updated,
            "defensive_mode": self.defensive_mode,
            "consecutive_bad_outcomes": self.consecutive_bad_outcomes,
            "candidate_summaries": [
                candidate.as_dict()
                for candidate in self.candidate_summaries
            ],
            "notes": list(self.notes),
        }


class ContinuousLearningEngine:
    """
    Safe continuous-learning layer.

    The engine learns only from RESOLVED historical outcomes.

    It may:
    - aggregate repeated regimes / patterns / context tags,
    - measure empirical success/failure rates,
    - create or update KnowledgeBase lessons,
    - expose defensive-mode state after repeated bad outcomes.

    It does NOT:
    - edit Python source code,
    - execute trades,
    - rewrite live strategy weights,
    - promote weak findings from tiny samples,
    - use unresolved/future outcomes.

    Stable learning therefore follows:

        observation
            -> enough samples
            -> candidate lesson
            -> validation threshold
            -> KnowledgeBase

    Champion/challenger model promotion remains a separate later responsibility.
    """

    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
        knowledge: Optional[KnowledgeBase] = None,
        journal: Optional[TradeJournal] = None,
    ) -> None:
        self.memory = memory or MemoryManager()
        self.knowledge = knowledge or KnowledgeBase()
        self.journal = journal or TradeJournal()

        self._last_report: Optional[LearningReport] = None

    @property
    def enabled(self) -> bool:
        return bool(CONFIG.LEARNING_ENABLED)

    @property
    def last_report(self) -> Optional[LearningReport]:
        return self._last_report

    def learn(
        self,
        *,
        asset: Optional[str] = None,
        max_cases: int = 5000,
    ) -> LearningReport:
        """
        Run one learning pass over already resolved memory cases.

        Nothing is learned from an unresolved case.
        """

        if max_cases <= 0:
            raise ValueError("max_cases must be greater than zero.")

        if not self.enabled:
            report = LearningReport(
                generated_at=time.time(),
                resolved_cases_scanned=0,
                candidates_found=0,
                candidates_promoted=0,
                knowledge_updated=0,
                defensive_mode=False,
                consecutive_bad_outcomes=0,
                notes=("continuous learning is disabled",),
            )
            self._last_report = report
            return report

        cases = self.memory.recent_cases(
            limit=max_cases,
            resolved_only=True,
            asset=asset,
        )

        candidates = self._build_candidates(cases)

        promoted = 0
        updated = 0

        for candidate in candidates:
            if not self._eligible_for_knowledge(candidate):
                continue

            existing = self._find_existing_knowledge(candidate)

            if existing is None:
                self.knowledge.add(
                    category=candidate.category,
                    title=candidate.title,
                    description=candidate.description,
                    direction=candidate.direction,
                    regime=candidate.regime,
                    confidence=candidate.confidence,
                    reliability=candidate.reliability,
                    tags=candidate.tags,
                    evidence={
                        **dict(candidate.evidence),
                        "learning_key": candidate.key,
                        "observations": candidate.observations,
                        "successes": candidate.successes,
                        "failures": candidate.failures,
                        "success_rate": candidate.success_rate,
                        "source": "continuous_learning",
                    },
                )
                promoted += 1
            else:
                self._update_existing_knowledge(
                    existing=existing,
                    candidate=candidate,
                )
                updated += 1

        consecutive_bad = self.consecutive_bad_outcomes()
        defensive_mode = (
            consecutive_bad
            >= CONFIG.MAX_CONSECUTIVE_BAD_OUTCOMES
        )

        notes: list[str] = []

        if len(cases) < CONFIG.LEARNING_MIN_NEW_CASES:
            notes.append(
                "resolved sample is still below the preferred learning threshold"
            )

        if defensive_mode:
            notes.append(
                "defensive mode is active because recent outcomes are poor"
            )

        if not candidates:
            notes.append(
                "no repeated learning candidates were found"
            )

        report = LearningReport(
            generated_at=time.time(),
            resolved_cases_scanned=len(cases),
            candidates_found=len(candidates),
            candidates_promoted=promoted,
            knowledge_updated=updated,
            defensive_mode=defensive_mode,
            consecutive_bad_outcomes=consecutive_bad,
            candidate_summaries=tuple(candidates[:50]),
            notes=tuple(notes),
        )

        self._last_report = report
        return report

    def runtime_context(self) -> dict[str, Any]:
        """
        Small context object intended for RiskAgent / Orchestrator.
        """

        consecutive_bad = self.consecutive_bad_outcomes()

        return {
            "consecutive_bad_outcomes": consecutive_bad,
            "defensive_mode": (
                consecutive_bad
                >= CONFIG.MAX_CONSECUTIVE_BAD_OUTCOMES
            ),
            "learning_enabled": self.enabled,
        }

    def consecutive_bad_outcomes(
        self,
        limit: int = 50,
    ) -> int:
        """
        Count consecutive negative resolved outcomes, newest first.

        Memory outcomes are the canonical source because they are tied directly
        to analyzed market cases.
        """

        cases = self.memory.recent_cases(
            limit=limit,
            resolved_only=True,
        )

        count = 0

        for case in cases:
            score = case.outcome_score

            if score is None:
                continue

            if score < 0:
                count += 1
                continue

            break

        return count

    def performance_snapshot(
        self,
        *,
        asset: Optional[str] = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        cases = self.memory.recent_cases(
            limit=limit,
            resolved_only=True,
            asset=asset,
        )

        if not cases:
            return {
                "resolved_cases": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "positive_rate": None,
                "average_outcome": None,
                "average_confidence": None,
            }

        scores = [
            float(case.outcome_score)
            for case in cases
            if case.outcome_score is not None
        ]

        positive = sum(
            1
            for score in scores
            if score > 0
        )

        negative = sum(
            1
            for score in scores
            if score < 0
        )

        neutral = (
            len(scores)
            - positive
            - negative
        )

        confidence_values = [
            case.confidence
            for case in cases
        ]

        return {
            "resolved_cases": len(scores),
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "positive_rate": (
                positive / len(scores)
                if scores
                else None
            ),
            "average_outcome": (
                sum(scores) / len(scores)
                if scores
                else None
            ),
            "average_confidence": (
                sum(confidence_values)
                / len(confidence_values)
                if confidence_values
                else None
            ),
        }

    def _build_candidates(
        self,
        cases: Sequence[MemoryCase],
    ) -> list[LearningCandidate]:
        """
        Build candidates at three levels:

        1) regime + direction
        2) regime + direction + one tag
        3) regime + direction + selected tag pairs

        This creates useful lessons without overfitting every unique case.
        """

        groups: dict[
            str,
            dict[str, Any],
        ] = {}

        for case in cases:
            if case.outcome_score is None:
                continue

            descriptors = self._case_descriptors(case)

            for descriptor in descriptors:
                key = descriptor["key"]

                bucket = groups.setdefault(
                    key,
                    {
                        **descriptor,
                        "observations": 0,
                        "successes": 0,
                        "failures": 0,
                        "neutral": 0,
                        "outcome_sum": 0.0,
                        "confidence_sum": 0.0,
                        "uncertainty_sum": 0.0,
                    },
                )

                bucket["observations"] += 1
                bucket["outcome_sum"] += float(
                    case.outcome_score
                )
                bucket["confidence_sum"] += float(
                    case.confidence
                )
                bucket["uncertainty_sum"] += float(
                    case.uncertainty
                )

                if case.outcome_score > 0:
                    bucket["successes"] += 1
                elif case.outcome_score < 0:
                    bucket["failures"] += 1
                else:
                    bucket["neutral"] += 1

        candidates: list[LearningCandidate] = []

        for key, bucket in groups.items():
            observations = int(
                bucket["observations"]
            )
            successes = int(
                bucket["successes"]
            )
            failures = int(
                bucket["failures"]
            )

            resolved = successes + failures

            if resolved <= 0:
                continue

            success_rate = (
                successes
                / resolved
            )

            sample_strength = self._clip01(
                resolved
                / max(
                    CONFIG.LEARNING_MIN_VALIDATION_CASES,
                    1,
                )
            )

            edge = abs(
                success_rate
                - 0.50
            ) * 2.0

            consistency = self._clip01(
                1.0
                - (
                    bucket["uncertainty_sum"]
                    / observations
                )
            )

            average_confidence = self._clip01(
                bucket["confidence_sum"]
                / observations
            )

            reliability = self._clip01(
                0.45 * sample_strength
                + 0.35 * edge
                + 0.20 * consistency
            )

            confidence = self._clip01(
                0.45 * average_confidence
                + 0.35 * edge
                + 0.20 * sample_strength
            )

            empirical_direction = (
                bucket["direction"]
                if success_rate >= 0.50
                else self._opposite_direction(
                    bucket["direction"]
                )
            )

            description = self._candidate_description(
                regime=bucket["regime"],
                direction=bucket["direction"],
                empirical_direction=empirical_direction,
                tags=bucket["tags"],
                observations=observations,
                success_rate=success_rate,
            )

            candidates.append(
                LearningCandidate(
                    key=key,
                    category=bucket["category"],
                    title=bucket["title"],
                    description=description,
                    direction=empirical_direction,
                    regime=bucket["regime"],
                    observations=observations,
                    successes=successes,
                    failures=failures,
                    success_rate=float(
                        success_rate
                    ),
                    confidence=float(
                        confidence
                    ),
                    reliability=float(
                        reliability
                    ),
                    tags=tuple(
                        bucket["tags"]
                    ),
                    evidence={
                        "average_outcome": (
                            bucket["outcome_sum"]
                            / observations
                        ),
                        "average_case_confidence": (
                            bucket["confidence_sum"]
                            / observations
                        ),
                        "average_case_uncertainty": (
                            bucket["uncertainty_sum"]
                            / observations
                        ),
                        "sample_strength": sample_strength,
                        "edge": edge,
                    },
                )
            )

        candidates.sort(
            key=lambda candidate: (
                candidate.reliability,
                candidate.confidence,
                candidate.observations,
            ),
            reverse=True,
        )

        return candidates

    def _case_descriptors(
        self,
        case: MemoryCase,
    ) -> list[dict[str, Any]]:
        descriptors: list[
            dict[str, Any]
        ] = []

        clean_tags = tuple(
            sorted(
                {
                    str(tag).strip()
                    for tag in case.tags
                    if str(tag).strip()
                }
            )
        )

        base_key = (
            f"regime={case.regime}"
            f"|direction={case.direction}"
        )

        descriptors.append(
            {
                "key": base_key,
                "category": "REGIME",
                "title": (
                    f"{case.regime} / "
                    f"{case.direction}"
                ),
                "direction": case.direction,
                "regime": case.regime,
                "tags": (),
            }
        )

        for tag in clean_tags:
            tag_key = (
                f"{base_key}"
                f"|tag={tag}"
            )

            descriptors.append(
                {
                    "key": tag_key,
                    "category": "PATTERN",
                    "title": (
                        f"{tag} in "
                        f"{case.regime}"
                    ),
                    "direction": case.direction,
                    "regime": case.regime,
                    "tags": (tag,),
                }
            )

        # Limited tag pairs capture useful pattern combinations such as
        # compression + breakout without generating combinatorial explosion.
        selected_tags = clean_tags[:6]

        for index, left in enumerate(
            selected_tags
        ):
            for right in selected_tags[
                index + 1:
            ]:
                pair = tuple(
                    sorted(
                        (left, right)
                    )
                )

                pair_key = (
                    f"{base_key}"
                    f"|tags={pair[0]}+{pair[1]}"
                )

                descriptors.append(
                    {
                        "key": pair_key,
                        "category": "PATTERN",
                        "title": (
                            f"{pair[0]} + "
                            f"{pair[1]} "
                            f"in {case.regime}"
                        ),
                        "direction": case.direction,
                        "regime": case.regime,
                        "tags": pair,
                    }
                )

        return descriptors

    @staticmethod
    def _candidate_description(
        *,
        regime: str,
        direction: str,
        empirical_direction: str,
        tags: Iterable[str],
        observations: int,
        success_rate: float,
    ) -> str:
        tags = tuple(tags)

        context = (
            ", ".join(tags)
            if tags
            else "general regime behaviour"
        )

        if empirical_direction == direction:
            interpretation = (
                f"{direction} historically retained "
                f"positive support"
            )
        else:
            interpretation = (
                f"{direction} historically underperformed; "
                f"{empirical_direction} or WAIT deserves more weight"
            )

        return (
            f"In regime {regime}, context [{context}] was observed "
            f"{observations} times with empirical success rate "
            f"{success_rate:.1%}. {interpretation}."
        )

    @staticmethod
    def _eligible_for_knowledge(
        candidate: LearningCandidate,
    ) -> bool:
        if (
            candidate.resolved
            < CONFIG.LEARNING_MIN_NEW_CASES
        ):
            return False

        if candidate.reliability < 0.55:
            return False

        if candidate.confidence < 0.55:
            return False

        # Weak ~50/50 findings are not knowledge.
        if abs(
            candidate.success_rate
            - 0.50
        ) < 0.08:
            return False

        return True

    def _find_existing_knowledge(
        self,
        candidate: LearningCandidate,
    ) -> Optional[KnowledgeItem]:
        matches = self.knowledge.search(
            category=candidate.category,
            regime=candidate.regime,
            active_only=False,
            limit=500,
        )

        for item in matches:
            learning_key = item.evidence.get(
                "learning_key"
            )

            if learning_key == candidate.key:
                return item

        return None

    def _update_existing_knowledge(
        self,
        *,
        existing: KnowledgeItem,
        candidate: LearningCandidate,
    ) -> KnowledgeItem:
        """
        Smoothly update knowledge.

        Per-update movement is bounded by
        LEARNING_MAX_WEIGHT_CHANGE_PER_UPDATE to avoid catastrophic drift.
        """

        confidence_delta = self._bounded_delta(
            candidate.confidence
            - existing.confidence
        )

        reliability_delta = self._bounded_delta(
            candidate.reliability
            - existing.reliability
        )

        new_confidence = self._clip01(
            existing.confidence
            + confidence_delta
        )

        new_reliability = self._clip01(
            existing.reliability
            + reliability_delta
        )

        return self.knowledge.update(
            existing.knowledge_id,
            description=candidate.description,
            direction=candidate.direction,
            confidence=new_confidence,
            reliability=new_reliability,
            tags=candidate.tags,
            evidence={
                "learning_key": candidate.key,
                "observations": candidate.observations,
                "successes": candidate.successes,
                "failures": candidate.failures,
                "success_rate": candidate.success_rate,
                "candidate_confidence": candidate.confidence,
                "candidate_reliability": candidate.reliability,
                "last_learning_update": time.time(),
                "source": "continuous_learning",
            },
            active=True,
        )

    @staticmethod
    def _opposite_direction(
        direction: str,
    ) -> str:
        if direction == "BULLISH":
            return "BEARISH"

        if direction == "BEARISH":
            return "BULLISH"

        return "WAIT"

    @staticmethod
    def _bounded_delta(
        value: float,
    ) -> float:
        maximum = max(
            float(
                CONFIG.LEARNING_MAX_WEIGHT_CHANGE_PER_UPDATE
            ),
            0.0,
        )

        return min(
            max(
                float(value),
                -maximum,
            ),
            maximum,
        )

    @staticmethod
    def _clip01(
        value: float,
    ) -> float:
        return min(
            max(
                float(value),
                0.0,
            ),
            1.0,
        )
