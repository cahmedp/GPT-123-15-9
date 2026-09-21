from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class MarketSnapshot:
    """
    Unified market state container

    يجمع كل معلومات السوق الحالية
    قبل إرسالها إلى Agents
    """


    asset: str

    timeframe: int

    features: Dict[str, Any]

    state: Dict[str, Any]

    created_at: float

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )



class SnapshotBuilder:
    """
    بناء Snapshot من مخرجات
    Feature Engine + Market State
    """


    def create(
        self,
        features: dict,
        state: dict,
        timestamp: Optional[float] = None
    ) -> MarketSnapshot:


        if timestamp is None:

            timestamp = datetime.now().timestamp()



        return MarketSnapshot(

            asset=features["asset"],

            timeframe=features["timeframe"],

            features=features,

            state=state,

            created_at=timestamp,

            metadata={

                "source":
                "market_intelligence"

            }

        )