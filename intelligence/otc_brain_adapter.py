"""
OTC Brain Adapter

Converts existing engine outputs into OTCDecisionContext.

Responsibility:
- Mapping only.
- No strategy logic.
- No BUY/SELL generation.
"""

from intelligence.otc_decision_context import OTCDecisionContext


class OTCBrainAdapter:

    def build_context(
        self,
        market_result,
        setup_result,
        micro_result,
        pattern_result,
        liquidity_result,
        temporal_result,
        candle_result,
        conflict_result=None,
    ):

        return OTCDecisionContext(
            market_context=self._to_dict(market_result),
            setup_context=self._to_dict(setup_result),
            micro_context=self._to_dict(micro_result),
            pattern_context=self._to_dict(pattern_result),
            liquidity_context=self._to_dict(liquidity_result),
            temporal_context=self._to_dict(temporal_result),
            candle_context=self._to_dict(candle_result),
            conflict_context=self._to_dict(conflict_result),
        )

    def _to_dict(self, result):

        if result is None:
            return {}

        if isinstance(result, dict):
            return result

        if hasattr(result, "as_dict"):
            return result.as_dict()

        if hasattr(result, "__dict__"):
            return vars(result)

        return {"value": result}
