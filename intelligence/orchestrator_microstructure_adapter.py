"""
Orchestrator Microstructure Adapter

Purpose:
Convert real orchestrator final decision objects
into microstructure snapshots.

Rules:
- Observer only.
- No decision changes.
- No signal generation.
- No future data usage.
"""

from intelligence.microstructure_snapshot import create_snapshot


class OrchestratorMicrostructureAdapter:

    def build_snapshot(
        self,
        *,
        final,
        market,
        regime,
        candle_context,
    ):
        """
        Convert production objects into snapshot input.
        """

        micro = {
            "state": self._get(
                candle_context,
                "micro_state",
                "UNKNOWN"
            ),
            "impulse_strength": self._get(
                candle_context,
                "impulse_strength",
                0.0
            ),
            "noise_score": self._get(
                candle_context,
                "noise_score",
                0.0
            ),
            "momentum_score": self._get(
                candle_context,
                "momentum_score",
                0.0
            ),
        }

        pattern = {
            "state": self._get(
                candle_context,
                "pattern_state",
                "UNKNOWN"
            )
        }

        liquidity = {
            "state": self._get(
                candle_context,
                "liquidity_state",
                "UNKNOWN"
            )
        }

        temporal = {
            "state": self._get(
                candle_context,
                "temporal_state",
                "UNKNOWN"
            )
        }

        decision = {
            "state": final.advisory_action,
            "evidence_score": final.calibrated_confidence,
            "execution_score": final.calibrated_confidence,
        }

        return create_snapshot(
            asset=final.asset,
            timeframe=candle_context["timeframe"],
            candle_id=candle_context["candle_id"],
            micro=micro,
            pattern=pattern,
            liquidity=liquidity,
            temporal=temporal,
            decision=decision,
        )


    def _get(self, obj, key, default):

        if isinstance(obj, dict):
            return obj.get(key, default)

        return getattr(
            obj,
            key,
            default
        )
