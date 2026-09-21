from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Mapping, Optional, Sequence

from config import CONFIG
from memory.knowledge_base import KnowledgeBase
from memory.memory_manager import MemoryCase, MemoryManager
from memory.trade_journal import TradeJournal


@dataclass(frozen=True, slots=True)
class LearningGoal:
    goal_id: str
    created_at: float
    updated_at: float

    name: str
    category: str
    description: str

    priority: float
    severity: float
    confidence: float

    metric_name: str
    current_value: float
    target_value: float

    status: str
    observations: int

    tags: tuple[str, ...] = field(default_factory=tuple)
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "priority": self.priority,
            "severity": self.severity,
            "confidence": self.confidence,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "status": self.status,
            "observations": self.observations,
            "tags": list(self.tags),
            "evidence": dict(self.evidence),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "LearningGoal":
        return cls(
            goal_id=str(payload["goal_id"]),
            created_at=float(payload["created_at"]),
            updated_at=float(payload["updated_at"]),
            name=str(payload.get("name", "")),
            category=str(
                payload.get(
                    "category",
                    "GENERAL",
                )
            ).upper(),
            description=str(
                payload.get(
                    "description",
                    "",
                )
            ),
            priority=float(
                payload.get(
                    "priority",
                    0.0,
                )
            ),
            severity=float(
                payload.get(
                    "severity",
                    0.0,
                )
            ),
            confidence=float(
                payload.get(
                    "confidence",
                    0.0,
                )
            ),
            metric_name=str(
                payload.get(
                    "metric_name",
                    "",
                )
            ),
            current_value=float(
                payload.get(
                    "current_value",
                    0.0,
                )
            ),
            target_value=float(
                payload.get(
                    "target_value",
                    0.0,
                )
            ),
            status=str(
                payload.get(
                    "status",
                    "ACTIVE",
                )
            ).upper(),
            observations=max(
                int(
                    payload.get(
                        "observations",
                        0,
                    )
                ),
                0,
            ),
            tags=tuple(
                str(tag)
                for tag in payload.get(
                    "tags",
                    [],
                )
            ),
            evidence=dict(
                payload.get(
                    "evidence",
                    {},
                )
            ),
        )


class GoalManager:
    """
    Autonomous improvement-goal manager.

    It does NOT rewrite source code and does NOT change live trading logic.

    It only:
    - reviews historical performance,
    - identifies recurring weaknesses,
    - creates measurable improvement goals,
    - tracks whether those weaknesses improve over time,
    - exposes priorities to Continuous Learning and reports.

    Example goals:
        - reduce fake-break false positives
        - improve confidence calibration
        - reduce high-confidence wrong calls
        - improve behaviour in transition regimes
        - reduce excessive WAIT when market quality is good
    """

    FILE_NAME = "goals.json"

    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
        knowledge: Optional[KnowledgeBase] = None,
        journal: Optional[TradeJournal] = None,
        path: Optional[Path | str] = None,
    ) -> None:
        self.memory = memory or MemoryManager()
        self.knowledge = knowledge or KnowledgeBase()
        self.journal = journal or TradeJournal()

        self.path = Path(
            path
            if path is not None
            else CONFIG.KNOWLEDGE_DIR / self.FILE_NAME
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = RLock()
        self._goals: dict[str, LearningGoal] = {}

        self._load()

    @property
    def enabled(self) -> bool:
        return bool(
            CONFIG.GOAL_MANAGER_ENABLED
        )

    def review(
        self,
        *,
        asset: Optional[str] = None,
        limit: int = 3000,
    ) -> list[LearningGoal]:
        """
        Review historical outcomes and refresh improvement goals.
        """

        if not self.enabled:
            return self.active_goals()

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        cases = self.memory.recent_cases(
            limit=limit,
            resolved_only=True,
            asset=asset,
        )

        if len(cases) < 20:
            return self.active_goals()

        candidates: list[
            dict[str, Any]
        ] = []

        candidates.extend(
            self._goal_high_confidence_errors(
                cases
            )
        )

        candidates.extend(
            self._goal_fake_break_quality(
                cases
            )
        )

        candidates.extend(
            self._goal_transition_regime(
                cases
            )
        )

        candidates.extend(
            self._goal_wait_quality(
                cases
            )
        )

        candidates.extend(
            self._goal_confidence_calibration(
                cases
            )
        )

        candidates.extend(
            self._goal_recent_deterioration(
                cases
            )
        )

        seen_names: set[str] = set()

        for candidate in candidates:
            name = str(
                candidate["name"]
            ).strip()

            if not name:
                continue

            seen_names.add(name)

            self._upsert_goal(
                **candidate
            )

        self._retire_missing_goals(
            seen_names
        )

        self._save()

        return self.active_goals()

    def active_goals(
        self,
        limit: int = 20,
    ) -> list[LearningGoal]:
        with self._lock:
            goals = [
                goal
                for goal in self._goals.values()
                if goal.status == "ACTIVE"
            ]

        goals.sort(
            key=lambda goal: (
                goal.priority,
                goal.severity,
                goal.confidence,
                goal.updated_at,
            ),
            reverse=True,
        )

        return goals[
            :max(
                int(limit),
                0,
            )
        ]

    def all_goals(
        self,
    ) -> list[LearningGoal]:
        with self._lock:
            goals = list(
                self._goals.values()
            )

        goals.sort(
            key=lambda goal: (
                goal.priority,
                goal.updated_at,
            ),
            reverse=True,
        )

        return goals

    def runtime_context(
        self,
    ) -> dict[str, Any]:
        goals = self.active_goals(
            limit=5
        )

        return {
            "active_goal_count": len(
                goals
            ),
            "top_goals": [
                {
                    "name": goal.name,
                    "priority": goal.priority,
                    "category": goal.category,
                    "current_value": goal.current_value,
                    "target_value": goal.target_value,
                }
                for goal in goals
            ],
        }

    def _goal_high_confidence_errors(
        self,
        cases: Sequence[MemoryCase],
    ) -> list[dict[str, Any]]:
        high_conf = [
            case
            for case in cases
            if case.confidence >= 0.75
            and case.outcome_score is not None
        ]

        if len(high_conf) < 15:
            return []

        wrong = [
            case
            for case in high_conf
            if case.outcome_score < 0
        ]

        rate = len(wrong) / len(
            high_conf
        )

        if rate < 0.20:
            return []

        severity = self._clip01(
            (rate - 0.20)
            / 0.40
        )

        return [
            {
                "name": "reduce_high_confidence_errors",
                "category": "CALIBRATION",
                "description": (
                    "Reduce cases where the system is highly confident "
                    "but the resolved outcome is negative."
                ),
                "priority": self._priority(
                    severity=severity,
                    sample_size=len(high_conf),
                ),
                "severity": severity,
                "confidence": self._sample_confidence(
                    len(high_conf)
                ),
                "metric_name": "high_confidence_error_rate",
                "current_value": rate,
                "target_value": 0.15,
                "observations": len(
                    high_conf
                ),
                "tags": (
                    "confidence",
                    "calibration",
                    "risk",
                ),
                "evidence": {
                    "high_confidence_cases": len(
                        high_conf
                    ),
                    "wrong_cases": len(
                        wrong
                    ),
                },
            }
        ]

    def _goal_fake_break_quality(
        self,
        cases: Sequence[MemoryCase],
    ) -> list[dict[str, Any]]:
        relevant = [
            case
            for case in cases
            if any(
                "fake_break"
                in tag.lower()
                or "fake-break"
                in tag.lower()
                for tag in case.tags
            )
            and case.outcome_score
            is not None
        ]

        if len(relevant) < 15:
            return []

        losses = sum(
            1
            for case in relevant
            if case.outcome_score < 0
        )

        loss_rate = losses / len(
            relevant
        )

        if loss_rate < 0.35:
            return []

        severity = self._clip01(
            (loss_rate - 0.35)
            / 0.45
        )

        return [
            {
                "name": "improve_fake_break_filtering",
                "category": "PATTERN",
                "description": (
                    "Improve filtering of fake-break and liquidity-sweep "
                    "setups that historically produced negative outcomes."
                ),
                "priority": self._priority(
                    severity=severity,
                    sample_size=len(
                        relevant
                    ),
                ),
                "severity": severity,
                "confidence": self._sample_confidence(
                    len(relevant)
                ),
                "metric_name": "fake_break_loss_rate",
                "current_value": loss_rate,
                "target_value": 0.25,
                "observations": len(
                    relevant
                ),
                "tags": (
                    "fake_break",
                    "liquidity",
                    "rejection",
                ),
                "evidence": {
                    "cases": len(
                        relevant
                    ),
                    "losses": losses,
                },
            }
        ]

    def _goal_transition_regime(
        self,
        cases: Sequence[MemoryCase],
    ) -> list[dict[str, Any]]:
        relevant = [
            case
            for case in cases
            if "TRANSITION"
            in case.regime.upper()
            and case.outcome_score
            is not None
        ]

        if len(relevant) < 15:
            return []

        losses = sum(
            1
            for case in relevant
            if case.outcome_score < 0
        )

        loss_rate = losses / len(
            relevant
        )

        if loss_rate < 0.40:
            return []

        severity = self._clip01(
            (loss_rate - 0.40)
            / 0.40
        )

        return [
            {
                "name": "improve_transition_regime_handling",
                "category": "REGIME",
                "description": (
                    "Reduce directional errors while the market is changing "
                    "structure or showing unstable transition behaviour."
                ),
                "priority": self._priority(
                    severity=severity,
                    sample_size=len(
                        relevant
                    ),
                ),
                "severity": severity,
                "confidence": self._sample_confidence(
                    len(relevant)
                ),
                "metric_name": "transition_loss_rate",
                "current_value": loss_rate,
                "target_value": 0.30,
                "observations": len(
                    relevant
                ),
                "tags": (
                    "transition",
                    "choch",
                    "structure",
                ),
                "evidence": {
                    "cases": len(
                        relevant
                    ),
                    "losses": losses,
                },
            }
        ]

    def _goal_wait_quality(
        self,
        cases: Sequence[MemoryCase],
    ) -> list[dict[str, Any]]:
        wait_cases = [
            case
            for case in cases
            if case.direction == "WAIT"
        ]

        if len(wait_cases) < 25:
            return []

        wait_rate = len(
            wait_cases
        ) / len(
            cases
        )

        # Excessive WAIT is only a goal when it is very high.
        if wait_rate < 0.65:
            return []

        severity = self._clip01(
            (wait_rate - 0.65)
            / 0.25
        )

        return [
            {
                "name": "reduce_excessive_wait_rate",
                "category": "TIMING",
                "description": (
                    "Reduce excessive WAIT output while preserving safety, "
                    "especially when market quality is otherwise acceptable."
                ),
                "priority": self._priority(
                    severity=severity,
                    sample_size=len(
                        cases
                    ),
                ),
                "severity": severity,
                "confidence": self._sample_confidence(
                    len(cases)
                ),
                "metric_name": "wait_rate",
                "current_value": wait_rate,
                "target_value": 0.50,
                "observations": len(
                    cases
                ),
                "tags": (
                    "wait",
                    "timing",
                    "opportunity",
                ),
                "evidence": {
                    "total_cases": len(
                        cases
                    ),
                    "wait_cases": len(
                        wait_cases
                    ),
                },
            }
        ]

    def _goal_confidence_calibration(
        self,
        cases: Sequence[MemoryCase],
    ) -> list[dict[str, Any]]:
        directional = [
            case
            for case in cases
            if case.direction
            in {
                "BULLISH",
                "BEARISH",
            }
            and case.outcome_score
            is not None
        ]

        if len(directional) < 30:
            return []

        observed_success = sum(
            1
            for case in directional
            if case.outcome_score > 0
        ) / len(
            directional
        )

        average_confidence = sum(
            case.confidence
            for case in directional
        ) / len(
            directional
        )

        calibration_error = abs(
            average_confidence
            - observed_success
        )

        if calibration_error < 0.10:
            return []

        severity = self._clip01(
            calibration_error
            / 0.30
        )

        return [
            {
                "name": "improve_confidence_calibration",
                "category": "CALIBRATION",
                "description": (
                    "Bring reported confidence closer to the empirical "
                    "success rate of resolved directional analyses."
                ),
                "priority": self._priority(
                    severity=severity,
                    sample_size=len(
                        directional
                    ),
                ),
                "severity": severity,
                "confidence": self._sample_confidence(
                    len(directional)
                ),
                "metric_name": "confidence_calibration_error",
                "current_value": calibration_error,
                "target_value": 0.05,
                "observations": len(
                    directional
                ),
                "tags": (
                    "confidence",
                    "probability",
                    "calibration",
                ),
                "evidence": {
                    "average_confidence": average_confidence,
                    "observed_success_rate": observed_success,
                },
            }
        ]

    def _goal_recent_deterioration(
        self,
        cases: Sequence[MemoryCase],
    ) -> list[dict[str, Any]]:
        if len(cases) < 60:
            return []

        recent = list(
            cases[:30]
        )

        older = list(
            cases[30:60]
        )

        recent_rate = self._positive_rate(
            recent
        )

        older_rate = self._positive_rate(
            older
        )

        if (
            recent_rate is None
            or older_rate is None
        ):
            return []

        deterioration = (
            older_rate
            - recent_rate
        )

        if deterioration < 0.15:
            return []

        severity = self._clip01(
            deterioration
            / 0.35
        )

        return [
            {
                "name": "investigate_recent_performance_deterioration",
                "category": "GENERAL",
                "description": (
                    "Investigate why the most recent resolved cases perform "
                    "materially worse than the preceding historical window."
                ),
                "priority": self._priority(
                    severity=severity,
                    sample_size=60,
                ),
                "severity": severity,
                "confidence": self._sample_confidence(
                    60
                ),
                "metric_name": "recent_success_rate_drop",
                "current_value": deterioration,
                "target_value": 0.05,
                "observations": 60,
                "tags": (
                    "drift",
                    "performance",
                    "regime_change",
                ),
                "evidence": {
                    "recent_success_rate": recent_rate,
                    "previous_success_rate": older_rate,
                },
            }
        ]

    def _upsert_goal(
        self,
        *,
        name: str,
        category: str,
        description: str,
        priority: float,
        severity: float,
        confidence: float,
        metric_name: str,
        current_value: float,
        target_value: float,
        observations: int,
        tags: Iterable[str],
        evidence: Mapping[str, Any],
    ) -> LearningGoal:
        with self._lock:
            existing = self._find_by_name(
                name
            )

            now = time.time()

            if existing is None:
                goal = LearningGoal(
                    goal_id=uuid.uuid4().hex,
                    created_at=now,
                    updated_at=now,

                    name=name,
                    category=str(
                        category
                    ).upper(),
                    description=str(
                        description
                    ),

                    priority=self._clip01(
                        priority
                    ),
                    severity=self._clip01(
                        severity
                    ),
                    confidence=self._clip01(
                        confidence
                    ),

                    metric_name=str(
                        metric_name
                    ),
                    current_value=float(
                        current_value
                    ),
                    target_value=float(
                        target_value
                    ),

                    status="ACTIVE",
                    observations=max(
                        int(
                            observations
                        ),
                        0,
                    ),

                    tags=tuple(
                        sorted(
                            {
                                str(tag).strip()
                                for tag in tags
                                if str(tag).strip()
                            }
                        )
                    ),

                    evidence=dict(
                        evidence
                    ),
                )
            else:
                goal = LearningGoal(
                    goal_id=existing.goal_id,
                    created_at=existing.created_at,
                    updated_at=now,

                    name=existing.name,
                    category=str(
                        category
                    ).upper(),
                    description=str(
                        description
                    ),

                    priority=self._clip01(
                        priority
                    ),
                    severity=self._clip01(
                        severity
                    ),
                    confidence=self._clip01(
                        confidence
                    ),

                    metric_name=str(
                        metric_name
                    ),
                    current_value=float(
                        current_value
                    ),
                    target_value=float(
                        target_value
                    ),

                    status="ACTIVE",
                    observations=max(
                        int(
                            observations
                        ),
                        0,
                    ),

                    tags=tuple(
                        sorted(
                            {
                                str(tag).strip()
                                for tag in tags
                                if str(tag).strip()
                            }
                        )
                    ),

                    evidence={
                        **dict(
                            existing.evidence
                        ),
                        **dict(
                            evidence
                        ),
                    },
                )

            self._goals[
                goal.goal_id
            ] = goal

            return goal

    def _retire_missing_goals(
        self,
        active_names: set[str],
    ) -> None:
        with self._lock:
            for goal_id, goal in list(
                self._goals.items()
            ):
                if (
                    goal.status != "ACTIVE"
                    or goal.name
                    in active_names
                ):
                    continue

                self._goals[
                    goal_id
                ] = LearningGoal(
                    goal_id=goal.goal_id,
                    created_at=goal.created_at,
                    updated_at=time.time(),

                    name=goal.name,
                    category=goal.category,
                    description=goal.description,

                    priority=goal.priority,
                    severity=goal.severity,
                    confidence=goal.confidence,

                    metric_name=goal.metric_name,
                    current_value=goal.current_value,
                    target_value=goal.target_value,

                    status="RESOLVED",
                    observations=goal.observations,

                    tags=goal.tags,
                    evidence=goal.evidence,
                )

    def _find_by_name(
        self,
        name: str,
    ) -> Optional[LearningGoal]:
        for goal in self._goals.values():
            if goal.name == name:
                return goal

        return None

    @staticmethod
    def _positive_rate(
        cases: Sequence[MemoryCase],
    ) -> Optional[float]:
        resolved = [
            case
            for case in cases
            if case.outcome_score
            is not None
        ]

        if not resolved:
            return None

        positive = sum(
            1
            for case in resolved
            if case.outcome_score > 0
        )

        return (
            positive
            / len(
                resolved
            )
        )

    @staticmethod
    def _priority(
        *,
        severity: float,
        sample_size: int,
    ) -> float:
        sample_confidence = (
            GoalManager._sample_confidence(
                sample_size
            )
        )

        return GoalManager._clip01(
            0.70
            * severity
            + 0.30
            * sample_confidence
        )

    @staticmethod
    def _sample_confidence(
        sample_size: int,
    ) -> float:
        return GoalManager._clip01(
            sample_size
            / max(
                CONFIG.GOAL_REVIEW_INTERVAL_CASES,
                1,
            )
        )

    def _load(
        self,
    ) -> None:
        if not self.path.exists():
            self._save()
            return

        try:
            raw = self.path.read_text(
                encoding="utf-8"
            ).strip()

            if not raw:
                return

            payload = json.loads(
                raw
            )

            loaded: dict[
                str,
                LearningGoal,
            ] = {}

            for row in payload.get(
                "goals",
                []
            ):
                try:
                    goal = (
                        LearningGoal.from_dict(
                            row
                        )
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue

                loaded[
                    goal.goal_id
                ] = goal

            self._goals = loaded

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
        ):
            self._goals = {}

    def _save(
        self,
    ) -> None:
        payload = {
            "version": 1,
            "saved_at": time.time(),
            "goals": [
                goal.as_dict()
                for goal in sorted(
                    self._goals.values(),
                    key=lambda value: (
                        value.created_at,
                        value.goal_id,
                    ),
                )
            ],
        }

        temporary = self.path.with_suffix(
            self.path.suffix
            + ".tmp"
        )

        temporary.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary.replace(
            self.path
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
