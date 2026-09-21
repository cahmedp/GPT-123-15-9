from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Mapping, Optional

from config import CONFIG


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    """
    One durable piece of learned knowledge.

    category examples:
        PATTERN
        REGIME
        RISK
        TIMING
        FAILURE
        SUCCESS
        GENERAL

    direction:
        BULLISH | BEARISH | WAIT | NEUTRAL
    """

    knowledge_id: str
    created_at: float
    updated_at: float

    category: str
    title: str
    description: str

    direction: str
    regime: Optional[str]

    confidence: float
    reliability: float

    observations: int
    successes: int
    failures: int

    tags: tuple[str, ...] = field(default_factory=tuple)
    evidence: Mapping[str, Any] = field(default_factory=dict)

    active: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "direction": self.direction,
            "regime": self.regime,
            "confidence": self.confidence,
            "reliability": self.reliability,
            "observations": self.observations,
            "successes": self.successes,
            "failures": self.failures,
            "tags": list(self.tags),
            "evidence": dict(self.evidence),
            "active": self.active,
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "KnowledgeItem":
        return cls(
            knowledge_id=str(payload["knowledge_id"]),
            created_at=float(payload["created_at"]),
            updated_at=float(payload["updated_at"]),
            category=str(
                payload.get(
                    "category",
                    "GENERAL",
                )
            ).upper(),
            title=str(payload.get("title", "")),
            description=str(
                payload.get(
                    "description",
                    "",
                )
            ),
            direction=str(
                payload.get(
                    "direction",
                    "NEUTRAL",
                )
            ).upper(),
            regime=(
                str(payload["regime"])
                if payload.get("regime") is not None
                else None
            ),
            confidence=float(
                payload.get(
                    "confidence",
                    0.0,
                )
            ),
            reliability=float(
                payload.get(
                    "reliability",
                    0.0,
                )
            ),
            observations=max(
                int(
                    payload.get(
                        "observations",
                        0,
                    )
                ),
                0,
            ),
            successes=max(
                int(
                    payload.get(
                        "successes",
                        0,
                    )
                ),
                0,
            ),
            failures=max(
                int(
                    payload.get(
                        "failures",
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
            active=bool(
                payload.get(
                    "active",
                    True,
                )
            ),
        )


class KnowledgeBase:
    """
    Durable knowledge layer.

    MemoryManager stores individual historical market cases.
    KnowledgeBase stores consolidated lessons extracted from many cases.

    Examples:
        - "Fake breaks after upper wick clusters are unreliable in high noise."
        - "1m breakout + retest aligned with 5m trend is historically stronger."
        - "Compression without 30s confirmation should remain WAIT."

    Important:
        - This class does NOT modify Python source code.
        - Learning changes knowledge records only.
        - Champion/challenger validation happens later before any learned
          configuration is trusted.
        - No trade execution exists here.
    """

    FILE_NAME = "knowledge.json"

    ALLOWED_DIRECTIONS = {
        "BULLISH",
        "BEARISH",
        "WAIT",
        "NEUTRAL",
    }

    def __init__(
        self,
        path: Optional[Path | str] = None,
    ) -> None:
        self.path = Path(
            path
            if path is not None
            else CONFIG.KNOWLEDGE_DIR
            / self.FILE_NAME
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = RLock()
        self._items: dict[
            str,
            KnowledgeItem,
        ] = {}

        self._load()

    def add(
        self,
        *,
        category: str,
        title: str,
        description: str,
        direction: str = "NEUTRAL",
        regime: Optional[str] = None,
        confidence: float = 0.50,
        reliability: float = 0.50,
        tags: Iterable[str] = (),
        evidence: Optional[
            Mapping[str, Any]
        ] = None,
        knowledge_id: Optional[str] = None,
    ) -> KnowledgeItem:
        category = self._normalize_text(
            category,
            fallback="GENERAL",
        ).upper()

        title = self._normalize_text(
            title
        )

        description = self._normalize_text(
            description
        )

        direction = self._normalize_direction(
            direction
        )

        if not title:
            raise ValueError(
                "Knowledge title cannot be empty."
            )

        if not description:
            raise ValueError(
                "Knowledge description cannot be empty."
            )

        now = time.time()

        item = KnowledgeItem(
            knowledge_id=(
                knowledge_id
                or uuid.uuid4().hex
            ),
            created_at=now,
            updated_at=now,

            category=category,
            title=title,
            description=description,

            direction=direction,
            regime=(
                str(regime)
                if regime is not None
                else None
            ),

            confidence=self._clip01(
                confidence
            ),
            reliability=self._clip01(
                reliability
            ),

            observations=0,
            successes=0,
            failures=0,

            tags=self._normalize_tags(
                tags
            ),
            evidence=dict(
                evidence or {}
            ),

            active=True,
        )

        with self._lock:
            if (
                item.knowledge_id
                in self._items
            ):
                raise ValueError(
                    f"Duplicate knowledge id: "
                    f"{item.knowledge_id}"
                )

            self._items[
                item.knowledge_id
            ] = item

            self._save()

        return item

    def record_observation(
        self,
        knowledge_id: str,
        *,
        successful: Optional[bool],
        confidence_delta: float = 0.0,
        evidence: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> KnowledgeItem:
        """
        Update one lesson after it is observed again.

        successful:
            True  -> supporting outcome
            False -> contradicting outcome
            None  -> observation without final result
        """

        with self._lock:
            previous = self._require(
                knowledge_id
            )

            observations = (
                previous.observations
                + 1
            )

            successes = previous.successes
            failures = previous.failures

            if successful is True:
                successes += 1

            elif successful is False:
                failures += 1

            resolved = (
                successes
                + failures
            )

            if resolved > 0:
                empirical_rate = (
                    successes
                    / resolved
                )
            else:
                empirical_rate = 0.50

            sample_strength = self._clip01(
                observations
                / max(
                    CONFIG.LEARNING_MIN_NEW_CASES,
                    1,
                )
            )

            reliability = self._clip01(
                0.70 * empirical_rate
                + 0.30 * sample_strength
            )

            confidence = self._clip01(
                previous.confidence
                + self._bounded_delta(
                    confidence_delta
                )
            )

            merged_evidence = dict(
                previous.evidence
            )

            if evidence:
                merged_evidence.update(
                    dict(evidence)
                )

            updated = KnowledgeItem(
                knowledge_id=previous.knowledge_id,
                created_at=previous.created_at,
                updated_at=time.time(),

                category=previous.category,
                title=previous.title,
                description=previous.description,

                direction=previous.direction,
                regime=previous.regime,

                confidence=confidence,
                reliability=reliability,

                observations=observations,
                successes=successes,
                failures=failures,

                tags=previous.tags,
                evidence=merged_evidence,

                active=previous.active,
            )

            self._items[
                knowledge_id
            ] = updated

            self._save()

            return updated

    def update(
        self,
        knowledge_id: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        direction: Optional[str] = None,
        regime: Optional[str] = None,
        confidence: Optional[float] = None,
        reliability: Optional[float] = None,
        tags: Optional[
            Iterable[str]
        ] = None,
        evidence: Optional[
            Mapping[str, Any]
        ] = None,
        active: Optional[bool] = None,
    ) -> KnowledgeItem:
        with self._lock:
            previous = self._require(
                knowledge_id
            )

            merged_evidence = dict(
                previous.evidence
            )

            if evidence is not None:
                merged_evidence.update(
                    dict(evidence)
                )

            updated = KnowledgeItem(
                knowledge_id=previous.knowledge_id,
                created_at=previous.created_at,
                updated_at=time.time(),

                category=previous.category,

                title=(
                    self._normalize_text(
                        title
                    )
                    if title is not None
                    else previous.title
                ),

                description=(
                    self._normalize_text(
                        description
                    )
                    if description is not None
                    else previous.description
                ),

                direction=(
                    self._normalize_direction(
                        direction
                    )
                    if direction is not None
                    else previous.direction
                ),

                regime=(
                    regime
                    if regime is not None
                    else previous.regime
                ),

                confidence=(
                    self._clip01(
                        confidence
                    )
                    if confidence is not None
                    else previous.confidence
                ),

                reliability=(
                    self._clip01(
                        reliability
                    )
                    if reliability is not None
                    else previous.reliability
                ),

                observations=previous.observations,
                successes=previous.successes,
                failures=previous.failures,

                tags=(
                    self._normalize_tags(
                        tags
                    )
                    if tags is not None
                    else previous.tags
                ),

                evidence=merged_evidence,

                active=(
                    bool(active)
                    if active is not None
                    else previous.active
                ),
            )

            self._items[
                knowledge_id
            ] = updated

            self._save()

            return updated

    def deactivate(
        self,
        knowledge_id: str,
    ) -> KnowledgeItem:
        return self.update(
            knowledge_id,
            active=False,
        )

    def activate(
        self,
        knowledge_id: str,
    ) -> KnowledgeItem:
        return self.update(
            knowledge_id,
            active=True,
        )

    def get(
        self,
        knowledge_id: str,
    ) -> Optional[KnowledgeItem]:
        with self._lock:
            return self._items.get(
                str(knowledge_id)
            )

    def all(
        self,
        *,
        active_only: bool = True,
    ) -> list[KnowledgeItem]:
        with self._lock:
            items = list(
                self._items.values()
            )

        if active_only:
            items = [
                item
                for item in items
                if item.active
            ]

        return sorted(
            items,
            key=lambda item: (
                item.reliability,
                item.confidence,
                item.observations,
                item.updated_at,
            ),
            reverse=True,
        )

    def search(
        self,
        *,
        category: Optional[str] = None,
        direction: Optional[str] = None,
        regime: Optional[str] = None,
        tags: Iterable[str] = (),
        min_confidence: float = 0.0,
        min_reliability: float = 0.0,
        active_only: bool = True,
        limit: int = 50,
    ) -> list[KnowledgeItem]:
        if limit <= 0:
            return []

        requested_tags = {
            str(tag).strip().lower()
            for tag in tags
            if str(tag).strip()
        }

        normalized_category = (
            str(category).strip().upper()
            if category is not None
            else None
        )

        normalized_direction = (
            self._normalize_direction(
                direction
            )
            if direction is not None
            else None
        )

        min_confidence = self._clip01(
            min_confidence
        )

        min_reliability = self._clip01(
            min_reliability
        )

        results: list[
            KnowledgeItem
        ] = []

        for item in self.all(
            active_only=active_only
        ):
            if (
                normalized_category
                is not None
                and item.category
                != normalized_category
            ):
                continue

            if (
                normalized_direction
                is not None
                and item.direction
                != normalized_direction
            ):
                continue

            if (
                regime is not None
                and item.regime
                != regime
            ):
                continue

            if (
                item.confidence
                < min_confidence
            ):
                continue

            if (
                item.reliability
                < min_reliability
            ):
                continue

            if requested_tags:
                item_tags = {
                    tag.lower()
                    for tag in item.tags
                }

                if not requested_tags.issubset(
                    item_tags
                ):
                    continue

            results.append(
                item
            )

            if len(results) >= limit:
                break

        return results

    def directional_support(
        self,
        *,
        regime: Optional[str] = None,
        tags: Iterable[str] = (),
    ) -> dict[str, float | int]:
        """
        Aggregate trusted knowledge into directional context.

        Returned values are evidence only; the final decision engine decides
        how much weight to give them.
        """

        items = self.search(
            regime=regime,
            tags=tags,
            min_confidence=0.35,
            min_reliability=0.35,
            active_only=True,
            limit=500,
        )

        bullish = 0.0
        bearish = 0.0
        wait = 0.0
        neutral = 0.0
        total = 0.0

        for item in items:
            sample_factor = self._clip01(
                item.observations
                / max(
                    CONFIG.MIN_SIMILAR_CASES_FOR_STRONG_MEMORY,
                    1,
                )
            )

            weight = (
                item.confidence
                * item.reliability
                * (
                    0.50
                    + 0.50
                    * sample_factor
                )
            )

            total += weight

            if item.direction == "BULLISH":
                bullish += weight
            elif item.direction == "BEARISH":
                bearish += weight
            elif item.direction == "WAIT":
                wait += weight
            else:
                neutral += weight

        if total <= 1e-12:
            return {
                "count": len(items),
                "bullish_support": 0.0,
                "bearish_support": 0.0,
                "wait_support": 0.0,
                "neutral_support": 0.0,
                "knowledge_confidence": 0.0,
            }

        knowledge_confidence = self._clip01(
            sum(
                item.confidence
                * item.reliability
                for item in items
            )
            / max(
                len(items),
                1,
            )
        )

        return {
            "count": len(items),
            "bullish_support": float(
                bullish / total
            ),
            "bearish_support": float(
                bearish / total
            ),
            "wait_support": float(
                wait / total
            ),
            "neutral_support": float(
                neutral / total
            ),
            "knowledge_confidence": float(
                knowledge_confidence
            ),
        }

    def summary(
        self,
    ) -> dict[str, Any]:
        items = self.all(
            active_only=False
        )

        active = [
            item
            for item in items
            if item.active
        ]

        total_observations = sum(
            item.observations
            for item in items
        )

        resolved = sum(
            item.successes
            + item.failures
            for item in items
        )

        successes = sum(
            item.successes
            for item in items
        )

        return {
            "total_items": len(items),
            "active_items": len(active),
            "inactive_items": (
                len(items)
                - len(active)
            ),
            "total_observations": int(
                total_observations
            ),
            "resolved_observations": int(
                resolved
            ),
            "empirical_success_rate": (
                float(
                    successes
                    / resolved
                )
                if resolved > 0
                else None
            ),
            "average_confidence": (
                float(
                    sum(
                        item.confidence
                        for item in active
                    )
                    / len(active)
                )
                if active
                else 0.0
            ),
            "average_reliability": (
                float(
                    sum(
                        item.reliability
                        for item in active
                    )
                    / len(active)
                )
                if active
                else 0.0
            ),
        }

    def _require(
        self,
        knowledge_id: str,
    ) -> KnowledgeItem:
        key = str(
            knowledge_id
        ).strip()

        item = self._items.get(
            key
        )

        if item is None:
            raise KeyError(
                f"Unknown knowledge item: {key}"
            )

        return item

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

            items = payload.get(
                "items",
                []
            )

            loaded: dict[
                str,
                KnowledgeItem,
            ] = {}

            for row in items:
                try:
                    item = (
                        KnowledgeItem.from_dict(
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
                    item.knowledge_id
                ] = item

            self._items = loaded

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
        ):
            self._items = {}

    def _save(
        self,
    ) -> None:
        payload = {
            "version": 1,
            "saved_at": time.time(),
            "items": [
                item.as_dict()
                for item in sorted(
                    self._items.values(),
                    key=lambda value: (
                        value.created_at,
                        value.knowledge_id,
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
    def _normalize_text(
        value: Any,
        fallback: str = "",
    ) -> str:
        text = str(
            value
            if value is not None
            else fallback
        ).strip()

        return text

    @classmethod
    def _normalize_direction(
        cls,
        value: Any,
    ) -> str:
        direction = str(
            value
            if value is not None
            else "NEUTRAL"
        ).strip().upper()

        if (
            direction
            not in cls.ALLOWED_DIRECTIONS
        ):
            raise ValueError(
                "direction must be "
                "BULLISH, BEARISH, WAIT or NEUTRAL."
            )

        return direction

    @staticmethod
    def _normalize_tags(
        tags: Iterable[str],
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(tag).strip()
                    for tag in tags
                    if str(tag).strip()
                }
            )
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
