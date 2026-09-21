from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Mapping, Optional, Sequence

from config import CONFIG


@dataclass(frozen=True, slots=True)
class MemoryCase:
    case_id: str
    created_at: float

    asset: str
    timeframe_seconds: int
    timestamp: float
    price: float

    regime: str
    market_state: str
    direction: str

    feature_vector: Mapping[str, float]
    tags: tuple[str, ...] = field(default_factory=tuple)

    confidence: float = 0.0
    uncertainty: float = 1.0

    outcome: Optional[str] = None
    outcome_score: Optional[float] = None
    outcome_timestamp: Optional[float] = None

    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "created_at": self.created_at,
            "asset": self.asset,
            "timeframe_seconds": self.timeframe_seconds,
            "timestamp": self.timestamp,
            "price": self.price,
            "regime": self.regime,
            "market_state": self.market_state,
            "direction": self.direction,
            "feature_vector": dict(self.feature_vector),
            "tags": list(self.tags),
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "outcome": self.outcome,
            "outcome_score": self.outcome_score,
            "outcome_timestamp": self.outcome_timestamp,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
    ) -> "MemoryCase":
        return cls(
            case_id=str(payload["case_id"]),
            created_at=float(payload["created_at"]),
            asset=str(payload["asset"]),
            timeframe_seconds=int(
                payload["timeframe_seconds"]
            ),
            timestamp=float(payload["timestamp"]),
            price=float(payload["price"]),
            regime=str(payload.get("regime", "UNKNOWN")),
            market_state=str(
                payload.get(
                    "market_state",
                    "UNKNOWN",
                )
            ),
            direction=str(
                payload.get(
                    "direction",
                    "WAIT",
                )
            ),
            feature_vector={
                str(key): float(value)
                for key, value in dict(
                    payload.get(
                        "feature_vector",
                        {},
                    )
                ).items()
                if _is_finite_number(value)
            },
            tags=tuple(
                str(tag)
                for tag in payload.get(
                    "tags",
                    [],
                )
            ),
            confidence=float(
                payload.get(
                    "confidence",
                    0.0,
                )
            ),
            uncertainty=float(
                payload.get(
                    "uncertainty",
                    1.0,
                )
            ),
            outcome=(
                str(payload["outcome"])
                if payload.get("outcome")
                is not None
                else None
            ),
            outcome_score=(
                float(payload["outcome_score"])
                if payload.get("outcome_score")
                is not None
                else None
            ),
            outcome_timestamp=(
                float(
                    payload[
                        "outcome_timestamp"
                    ]
                )
                if payload.get(
                    "outcome_timestamp"
                ) is not None
                else None
            ),
            notes=tuple(
                str(note)
                for note in payload.get(
                    "notes",
                    [],
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class SimilarMemory:
    case: MemoryCase

    similarity: float
    recency_score: float
    outcome_quality: float
    composite_score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "case": self.case.as_dict(),
            "similarity": self.similarity,
            "recency_score": self.recency_score,
            "outcome_quality": self.outcome_quality,
            "composite_score": self.composite_score,
        }


@dataclass(frozen=True, slots=True)
class MemorySummary:
    total_cases: int
    resolved_cases: int
    unresolved_cases: int

    bullish_cases: int
    bearish_cases: int
    wait_cases: int

    positive_outcomes: int
    negative_outcomes: int
    neutral_outcomes: int

    average_confidence: float
    average_uncertainty: float

    latest_case_timestamp: Optional[float]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MemoryManager:
    """
    Central long-term case memory.

    Storage format:
        storage/memory/cases.jsonl

    Responsibilities:
    - Save normalized market-analysis cases.
    - Persist them safely as JSONL.
    - Restore memory after restarting the bot.
    - Update outcomes after the real market result is known.
    - Search for historically similar cases.
    - Rank similar cases using similarity + recency + outcome quality.
    - Provide memory statistics to agents, learning, world model and reports.

    It does NOT self-modify strategy logic and does NOT make final decisions.
    """

    FILE_NAME = "cases.jsonl"

    def __init__(
        self,
        path: Optional[Path | str] = None,
        max_in_memory: Optional[int] = None,
    ) -> None:
        self.path = Path(
            path
            if path is not None
            else CONFIG.MEMORY_DIR
            / self.FILE_NAME
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.max_in_memory = int(
            max_in_memory
            if max_in_memory is not None
            else max(
                CONFIG.MAX_CANDLES_IN_MEMORY,
                CONFIG.MEMORY_MAX_SIMILAR_CASES
                * 20,
            )
        )

        if self.max_in_memory <= 0:
            raise ValueError(
                "max_in_memory must be positive."
            )

        self._lock = RLock()
        self._cases: list[MemoryCase] = []
        self._case_index: dict[
            str,
            int,
        ] = {}

        self._load()

    def add_case(
        self,
        *,
        asset: str,
        timeframe_seconds: int,
        timestamp: float,
        price: float,
        regime: str,
        market_state: str,
        direction: str,
        feature_vector: Mapping[
            str,
            Any,
        ],
        tags: Iterable[str] = (),
        confidence: float = 0.0,
        uncertainty: float = 1.0,
        notes: Iterable[str] = (),
        case_id: Optional[str] = None,
    ) -> MemoryCase:
        """
        Save a new unresolved historical case.
        """

        clean_features = self._clean_feature_vector(
            feature_vector
        )

        if not clean_features:
            raise ValueError(
                "feature_vector must contain at least one finite numeric value."
            )

        if not asset:
            raise ValueError(
                "asset cannot be empty."
            )

        if timeframe_seconds <= 0:
            raise ValueError(
                "timeframe_seconds must be positive."
            )

        if timestamp <= 0:
            raise ValueError(
                "timestamp must be positive."
            )

        if price <= 0:
            raise ValueError(
                "price must be positive."
            )

        direction = str(
            direction
        ).upper()

        if direction not in {
            "BULLISH",
            "BEARISH",
            "WAIT",
        }:
            raise ValueError(
                "direction must be BULLISH, BEARISH or WAIT."
            )

        case = MemoryCase(
            case_id=(
                case_id
                or uuid.uuid4().hex
            ),
            created_at=time.time(),

            asset=str(asset),
            timeframe_seconds=int(
                timeframe_seconds
            ),
            timestamp=float(timestamp),
            price=float(price),

            regime=str(regime),
            market_state=str(
                market_state
            ),
            direction=direction,

            feature_vector=clean_features,

            tags=tuple(
                sorted(
                    {
                        str(tag).strip()
                        for tag in tags
                        if str(tag).strip()
                    }
                )
            ),

            confidence=self._clip01(
                confidence
            ),
            uncertainty=self._clip01(
                uncertainty
            ),

            outcome=None,
            outcome_score=None,
            outcome_timestamp=None,

            notes=tuple(
                str(note).strip()
                for note in notes
                if str(note).strip()
            ),
        )

        with self._lock:
            if (
                case.case_id
                in self._case_index
            ):
                raise ValueError(
                    f"Duplicate memory case id: {case.case_id}"
                )

            self._cases.append(case)
            self._case_index[
                case.case_id
            ] = len(
                self._cases
            ) - 1

            self._trim_in_memory()
            self._rewrite_file()

        return case

    def update_outcome(
        self,
        case_id: str,
        *,
        outcome: str,
        outcome_score: float,
        outcome_timestamp: Optional[
            float
        ] = None,
        note: Optional[str] = None,
    ) -> MemoryCase:
        """
        Resolve an existing case after the real result becomes known.

        outcome examples:
            CORRECT
            WRONG
            NEUTRAL
            WIN
            LOSS
            EXPIRED
        """

        case_id = str(case_id).strip()

        if not case_id:
            raise ValueError(
                "case_id cannot be empty."
            )

        outcome = str(
            outcome
        ).strip().upper()

        if not outcome:
            raise ValueError(
                "outcome cannot be empty."
            )

        outcome_score = self._clip(
            float(outcome_score),
            -1.0,
            1.0,
        )

        resolved_at = (
            float(
                outcome_timestamp
            )
            if outcome_timestamp
            is not None
            else time.time()
        )

        with self._lock:
            index = self._case_index.get(
                case_id
            )

            if index is None:
                raise KeyError(
                    f"Unknown memory case: {case_id}"
                )

            previous = self._cases[
                index
            ]

            notes = list(
                previous.notes
            )

            if (
                note is not None
                and str(note).strip()
            ):
                notes.append(
                    str(note).strip()
                )

            updated = MemoryCase(
                case_id=previous.case_id,
                created_at=previous.created_at,

                asset=previous.asset,
                timeframe_seconds=previous.timeframe_seconds,
                timestamp=previous.timestamp,
                price=previous.price,

                regime=previous.regime,
                market_state=previous.market_state,
                direction=previous.direction,

                feature_vector=dict(
                    previous.feature_vector
                ),
                tags=previous.tags,

                confidence=previous.confidence,
                uncertainty=previous.uncertainty,

                outcome=outcome,
                outcome_score=outcome_score,
                outcome_timestamp=resolved_at,

                notes=tuple(notes),
            )

            self._cases[
                index
            ] = updated

            self._rewrite_file()

            return updated

    def get_case(
        self,
        case_id: str,
    ) -> Optional[MemoryCase]:
        with self._lock:
            index = self._case_index.get(
                str(case_id)
            )

            if index is None:
                return None

            return self._cases[
                index
            ]

    def recent_cases(
        self,
        limit: int = 100,
        *,
        resolved_only: bool = False,
        asset: Optional[str] = None,
        timeframe_seconds: Optional[
            int
        ] = None,
    ) -> list[MemoryCase]:
        if limit <= 0:
            return []

        with self._lock:
            cases = list(
                self._cases
            )

        filtered: list[
            MemoryCase
        ] = []

        for case in reversed(
            cases
        ):
            if (
                resolved_only
                and case.outcome
                is None
            ):
                continue

            if (
                asset is not None
                and case.asset
                != asset
            ):
                continue

            if (
                timeframe_seconds
                is not None
                and case.timeframe_seconds
                != timeframe_seconds
            ):
                continue

            filtered.append(
                case
            )

            if len(
                filtered
            ) >= limit:
                break

        return filtered

    def find_similar(
        self,
        feature_vector: Mapping[
            str,
            Any,
        ],
        *,
        asset: Optional[str] = None,
        timeframe_seconds: Optional[
            int
        ] = None,
        regime: Optional[str] = None,
        direction: Optional[str] = None,
        resolved_only: bool = True,
        limit: int = CONFIG.MEMORY_MAX_SIMILAR_CASES,
        min_similarity: float = 0.0,
        reference_time: Optional[
            float
        ] = None,
    ) -> list[SimilarMemory]:
        """
        Search historical cases using numeric feature similarity.

        Ranking uses:
            similarity
            recency
            historical outcome quality

        This function never uses future data relative to `reference_time`.
        """

        query = self._clean_feature_vector(
            feature_vector
        )

        if not query:
            return []

        if limit <= 0:
            return []

        min_similarity = self._clip01(
            min_similarity
        )

        now = (
            float(reference_time)
            if reference_time
            is not None
            else time.time()
        )

        with self._lock:
            candidates = list(
                self._cases
            )

        results: list[
            SimilarMemory
        ] = []

        for case in candidates:
            if (
                case.timestamp
                >= now
            ):
                continue

            if (
                resolved_only
                and case.outcome
                is None
            ):
                continue

            if (
                asset is not None
                and case.asset
                != asset
            ):
                continue

            if (
                timeframe_seconds
                is not None
                and case.timeframe_seconds
                != timeframe_seconds
            ):
                continue

            if (
                regime is not None
                and case.regime
                != regime
            ):
                continue

            if (
                direction is not None
                and case.direction
                != direction
            ):
                continue

            similarity = (
                self._cosine_similarity(
                    query,
                    case.feature_vector,
                )
            )

            if similarity < min_similarity:
                continue

            recency_score = (
                self._recency_score(
                    case_timestamp=case.timestamp,
                    reference_time=now,
                )
            )

            outcome_quality = (
                self._outcome_quality(
                    case
                )
            )

            composite = self._clip01(
                CONFIG.MEMORY_SIMILARITY_WEIGHT
                * similarity
                + CONFIG.MEMORY_RECENCY_WEIGHT
                * recency_score
                + CONFIG.MEMORY_OUTCOME_WEIGHT
                * outcome_quality
            )

            results.append(
                SimilarMemory(
                    case=case,
                    similarity=float(
                        similarity
                    ),
                    recency_score=float(
                        recency_score
                    ),
                    outcome_quality=float(
                        outcome_quality
                    ),
                    composite_score=float(
                        composite
                    ),
                )
            )

        results.sort(
            key=lambda item: (
                item.composite_score,
                item.similarity,
                item.case.timestamp,
            ),
            reverse=True,
        )

        return results[:limit]

    def summarize_similar(
        self,
        similar_cases: Sequence[
            SimilarMemory
        ],
    ) -> dict[str, Any]:
        """
        Convert similar cases into compact evidence for agents/simulation.
        """

        if not similar_cases:
            return {
                "count": 0,
                "bullish_support": 0.0,
                "bearish_support": 0.0,
                "wait_support": 0.0,
                "positive_outcome_rate": None,
                "average_similarity": 0.0,
                "memory_confidence": 0.0,
            }

        bullish = 0.0
        bearish = 0.0
        wait = 0.0

        positive_weight = 0.0
        resolved_weight = 0.0
        similarity_sum = 0.0

        total_weight = 0.0

        for item in similar_cases:
            weight = max(
                item.composite_score,
                1e-9,
            )

            total_weight += weight
            similarity_sum += (
                item.similarity
                * weight
            )

            if item.case.direction == "BULLISH":
                bullish += weight
            elif item.case.direction == "BEARISH":
                bearish += weight
            else:
                wait += weight

            if (
                item.case.outcome_score
                is not None
            ):
                resolved_weight += weight

                if (
                    item.case.outcome_score
                    > 0
                ):
                    positive_weight += (
                        weight
                        * min(
                            item.case.outcome_score,
                            1.0,
                        )
                    )

        if total_weight <= 1e-12:
            total_weight = 1.0

        if resolved_weight > 1e-12:
            positive_rate: Optional[
                float
            ] = self._clip01(
                positive_weight
                / resolved_weight
            )
        else:
            positive_rate = None

        count_factor = self._clip01(
            len(similar_cases)
            / max(
                CONFIG.MIN_SIMILAR_CASES_FOR_STRONG_MEMORY,
                1,
            )
        )

        avg_similarity = (
            similarity_sum
            / total_weight
        )

        memory_confidence = self._clip01(
            0.60 * avg_similarity
            + 0.40 * count_factor
        )

        return {
            "count": len(
                similar_cases
            ),
            "bullish_support": self._clip01(
                bullish
                / total_weight
            ),
            "bearish_support": self._clip01(
                bearish
                / total_weight
            ),
            "wait_support": self._clip01(
                wait
                / total_weight
            ),
            "positive_outcome_rate": (
                float(
                    positive_rate
                )
                if positive_rate
                is not None
                else None
            ),
            "average_similarity": float(
                avg_similarity
            ),
            "memory_confidence": float(
                memory_confidence
            ),
        }

    def summary(
        self,
    ) -> MemorySummary:
        with self._lock:
            cases = list(
                self._cases
            )

        total = len(cases)

        resolved = [
            case
            for case in cases
            if case.outcome
            is not None
        ]

        unresolved = total - len(
            resolved
        )

        bullish = sum(
            case.direction
            == "BULLISH"
            for case in cases
        )
        bearish = sum(
            case.direction
            == "BEARISH"
            for case in cases
        )
        wait = sum(
            case.direction
            == "WAIT"
            for case in cases
        )

        positive = sum(
            1
            for case in resolved
            if (
                case.outcome_score
                is not None
                and case.outcome_score
                > 0
            )
        )

        negative = sum(
            1
            for case in resolved
            if (
                case.outcome_score
                is not None
                and case.outcome_score
                < 0
            )
        )

        neutral = (
            len(resolved)
            - positive
            - negative
        )

        average_confidence = (
            sum(
                case.confidence
                for case in cases
            ) / total
            if total
            else 0.0
        )

        average_uncertainty = (
            sum(
                case.uncertainty
                for case in cases
            ) / total
            if total
            else 0.0
        )

        latest_timestamp = (
            max(
                case.timestamp
                for case in cases
            )
            if cases
            else None
        )

        return MemorySummary(
            total_cases=total,
            resolved_cases=len(
                resolved
            ),
            unresolved_cases=unresolved,

            bullish_cases=int(
                bullish
            ),
            bearish_cases=int(
                bearish
            ),
            wait_cases=int(wait),

            positive_outcomes=positive,
            negative_outcomes=negative,
            neutral_outcomes=neutral,

            average_confidence=float(
                average_confidence
            ),
            average_uncertainty=float(
                average_uncertainty
            ),

            latest_case_timestamp=(
                float(
                    latest_timestamp
                )
                if latest_timestamp
                is not None
                else None
            ),
        )

    def export_cases(
        self,
    ) -> list[dict[str, Any]]:
        with self._lock:
            return [
                case.as_dict()
                for case in self._cases
            ]

    def _load(
        self,
    ) -> None:
        if not self.path.exists():
            self.path.touch()
            return

        loaded: list[
            MemoryCase
        ] = []

        try:
            with self.path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                for line in handle:
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        payload = json.loads(
                            line
                        )

                        case = (
                            MemoryCase.from_dict(
                                payload
                            )
                        )

                        loaded.append(
                            case
                        )

                    except (
                        json.JSONDecodeError,
                        KeyError,
                        TypeError,
                        ValueError,
                    ):
                        # A damaged row should not prevent the entire
                        # historical memory from loading.
                        continue

        except OSError:
            loaded = []

        loaded.sort(
            key=lambda case: (
                case.timestamp,
                case.created_at,
            )
        )

        if len(
            loaded
        ) > self.max_in_memory:
            loaded = loaded[
                -self.max_in_memory:
            ]

        self._cases = loaded

        self._rebuild_index()

    def _rewrite_file(
        self,
    ) -> None:
        temporary = self.path.with_suffix(
            self.path.suffix
            + ".tmp"
        )

        with temporary.open(
            "w",
            encoding="utf-8",
        ) as handle:
            for case in self._cases:
                handle.write(
                    json.dumps(
                        case.as_dict(),
                        ensure_ascii=False,
                        separators=(
                            ",",
                            ":",
                        ),
                    )
                )
                handle.write(
                    "\n"
                )

        temporary.replace(
            self.path
        )

    def _trim_in_memory(
        self,
    ) -> None:
        if len(
            self._cases
        ) <= self.max_in_memory:
            self._rebuild_index()
            return

        self._cases = self._cases[
            -self.max_in_memory:
        ]

        self._rebuild_index()

    def _rebuild_index(
        self,
    ) -> None:
        self._case_index = {
            case.case_id: index
            for index, case
            in enumerate(
                self._cases
            )
        }

    @staticmethod
    def _clean_feature_vector(
        feature_vector: Mapping[
            str,
            Any,
        ],
    ) -> dict[str, float]:
        clean: dict[
            str,
            float
        ] = {}

        for key, value in feature_vector.items():
            if not _is_finite_number(
                value
            ):
                continue

            clean[
                str(key)
            ] = float(value)

        return clean

    @staticmethod
    def _cosine_similarity(
        left: Mapping[
            str,
            float,
        ],
        right: Mapping[
            str,
            float,
        ],
    ) -> float:
        common_keys = (
            set(left)
            & set(right)
        )

        if not common_keys:
            return 0.0

        dot = sum(
            left[key]
            * right[key]
            for key in common_keys
        )

        left_norm = math.sqrt(
            sum(
                left[key] ** 2
                for key in common_keys
            )
        )

        right_norm = math.sqrt(
            sum(
                right[key] ** 2
                for key in common_keys
            )
        )

        denominator = (
            left_norm
            * right_norm
        )

        if denominator <= 1e-12:
            # All-zero aligned vectors are treated as uninformative.
            return 0.0

        cosine = (
            dot
            / denominator
        )

        # Convert -1..1 to 0..1.
        return MemoryManager._clip01(
            (cosine + 1.0) / 2.0
        )

    @staticmethod
    def _recency_score(
        *,
        case_timestamp: float,
        reference_time: float,
    ) -> float:
        age_seconds = max(
            reference_time
            - case_timestamp,
            0.0,
        )

        # Half-life-like decay of roughly one week. It does not erase old
        # knowledge; similarity and outcome quality still contribute.
        scale = (
            7.0
            * 24.0
            * 3600.0
        )

        return float(
            math.exp(
                -age_seconds
                / scale
            )
        )

    @staticmethod
    def _outcome_quality(
        case: MemoryCase,
    ) -> float:
        if (
            case.outcome_score
            is None
        ):
            return 0.50

        # Historical success gets a higher quality weight while failure
        # remains useful knowledge rather than being discarded.
        return MemoryManager._clip01(
            (
                case.outcome_score
                + 1.0
            )
            / 2.0
        )

    @staticmethod
    def flatten_numeric(
        payload: Any,
        *,
        prefix: str = "",
    ) -> dict[str, float]:
        """
        Convert nested dataclasses / mappings / simple objects into a flat
        numeric vector suitable for memory similarity.

        Booleans are encoded as 0/1.
        Strings and non-numeric values are ignored.
        """

        result: dict[
            str,
            float
        ] = {}

        def walk(
            value: Any,
            path: str,
        ) -> None:
            if value is None:
                return

            if isinstance(
                value,
                bool,
            ):
                result[path] = (
                    1.0
                    if value
                    else 0.0
                )
                return

            if _is_finite_number(
                value
            ):
                result[path] = float(
                    value
                )
                return

            if is_dataclass(
                value
            ):
                walk(
                    asdict(value),
                    path,
                )
                return

            if isinstance(
                value,
                Mapping,
            ):
                for key, child in value.items():
                    child_path = (
                        f"{path}.{key}"
                        if path
                        else str(key)
                    )

                    walk(
                        child,
                        child_path,
                    )

                return

            if isinstance(
                value,
                Sequence,
            ) and not isinstance(
                value,
                (
                    str,
                    bytes,
                    bytearray,
                ),
            ):
                for index, child in enumerate(
                    value
                ):
                    child_path = (
                        f"{path}[{index}]"
                        if path
                        else f"[{index}]"
                    )

                    walk(
                        child,
                        child_path,
                    )

        walk(
            payload,
            prefix,
        )

        return {
            key: value
            for key, value
            in result.items()
            if key
        }

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
    def _clip(
        value: float,
        low: float,
        high: float,
    ) -> float:
        return min(
            max(
                float(value),
                low,
            ),
            high,
        )


def _is_finite_number(
    value: Any,
) -> bool:
    if isinstance(
        value,
        bool,
    ):
        return True

    if not isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return False

    return math.isfinite(
        float(value)
    )
