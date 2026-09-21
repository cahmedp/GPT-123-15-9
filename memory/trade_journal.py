from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from threading import RLock
from typing import Any, Optional, Mapping


@dataclass(frozen=True, slots=True)
class JournalEntry:
    id: str
    created_at: float

    asset: str
    direction: str
    confidence: float

    price: float
    expiry_seconds: int

    analysis: Mapping[str, Any]

    result: Optional[str] = None
    pnl: Optional[float] = None
    closed_at: Optional[float] = None

    def to_dict(self):
        return asdict(self)


class TradeJournal:
    """
    Execution history journal.

    Stores:
    - every analyzed opportunity
    - final direction
    - confidence
    - reasoning snapshot
    - later outcome

    Used by:
    - memory system
    - continuous learning
    - performance analytics

    It does not execute trades.
    """

    def __init__(self, path: str = "storage/journal/trades.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.lock = RLock()
        self.entries: list[JournalEntry] = []

        self._load()

    def create(
        self,
        *,
        asset: str,
        direction: str,
        confidence: float,
        price: float,
        expiry_seconds: int,
        analysis: Mapping[str, Any],
    ) -> JournalEntry:

        entry = JournalEntry(
            id=uuid.uuid4().hex,
            created_at=time.time(),
            asset=asset,
            direction=direction,
            confidence=float(confidence),
            price=float(price),
            expiry_seconds=int(expiry_seconds),
            analysis=dict(analysis),
        )

        with self.lock:
            self.entries.append(entry)
            self._save()

        return entry

    def close(
        self,
        entry_id: str,
        result: str,
        pnl: float,
    ) -> Optional[JournalEntry]:

        with self.lock:
            for index, entry in enumerate(self.entries):

                if entry.id != entry_id:
                    continue

                updated = JournalEntry(
                    id=entry.id,
                    created_at=entry.created_at,
                    asset=entry.asset,
                    direction=entry.direction,
                    confidence=entry.confidence,
                    price=entry.price,
                    expiry_seconds=entry.expiry_seconds,
                    analysis=entry.analysis,
                    result=result,
                    pnl=float(pnl),
                    closed_at=time.time(),
                )

                self.entries[index] = updated
                self._save()

                return updated

        return None

    def recent(self, limit: int = 50):
        with self.lock:
            return list(reversed(self.entries[-limit:]))

    def statistics(self):
        with self.lock:
            closed = [
                e for e in self.entries
                if e.result is not None
            ]

        wins = sum(
            1 for e in closed
            if e.pnl is not None and e.pnl > 0
        )

        losses = sum(
            1 for e in closed
            if e.pnl is not None and e.pnl < 0
        )

        return {
            "total": len(self.entries),
            "closed": len(closed),
            "wins": wins,
            "losses": losses,
            "win_rate": (
                wins / len(closed)
                if closed else 0.0
            ),
        }

    def _load(self):
        if not self.path.exists():
            return

        try:
            with self.path.open(
                "r",
                encoding="utf-8",
            ) as f:

                for line in f:
                    if line.strip():
                        self.entries.append(
                            JournalEntry(
                                **json.loads(line)
                            )
                        )

        except Exception:
            self.entries = []

    def _save(self):
        temp = self.path.with_suffix(".tmp")

        with temp.open(
            "w",
            encoding="utf-8",
        ) as f:

            for entry in self.entries:
                f.write(
                    json.dumps(
                        entry.to_dict(),
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        temp.replace(self.path)
