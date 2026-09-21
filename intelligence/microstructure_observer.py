"""
Microstructure Observer

Bridge between orchestrator events and microstructure learning layer.

Responsibilities:
- receive completed decisions
- create snapshots
- register tracking
- validate closed candles

Does NOT change decisions.
"""

from intelligence.microstructure_snapshot import create_snapshot


class MicrostructureObserver:

    def __init__(self, tracker):
        self.tracker = tracker


    def on_decision(
        self,
        asset,
        timeframe,
        candle_id,
        micro,
        pattern,
        liquidity,
        temporal,
        decision,
    ):

        snapshot = create_snapshot(
            asset,
            timeframe,
            candle_id,
            micro,
            pattern,
            liquidity,
            temporal,
            decision,
        )

        return self.tracker.register_snapshot(snapshot)


    def on_candle_close(
        self,
        snapshot_id,
        candle_result
    ):

        return self.tracker.validate_closed_candle(
            snapshot_id,
            candle_result
        )
