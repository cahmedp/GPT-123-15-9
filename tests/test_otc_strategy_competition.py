"""
OTC Strategy Competition Layer Test

Fixed version:
- Includes ADX and ATR7 weighting functions.
- Ranks strategies for 30s OTC execution.
"""

from dataclasses import dataclass


@dataclass
class StrategyScore:
    strategy: str
    score: float
    reason: str


class OTCStrategyCompetition:

    @staticmethod
    def _adx_weight(adx: float) -> float:
        if adx >= 35:
            return 1.0
        if adx >= 25:
            return 0.85
        if adx >= 15:
            return 0.60
        return 0.30

    @staticmethod
    def _atr_weight(atr7: float) -> float:
        # 30s baseline volatility
        if atr7 >= 0.00015:
            return 1.0
        if atr7 >= 0.00008:
            return 0.80
        return 0.45

    def rank(
        self,
        market_pattern: str,
        noise: float,
        impulse: float,
        pressure: float,
        rejection: float,
        adx: float,
        atr7: float,
    ) -> dict:

        scores = []

        trend_strength = self._adx_weight(adx)
        volatility = self._atr_weight(atr7)

        def add(name, score, reason):
            scores.append(
                StrategyScore(
                    name,
                    round(max(0, min(score, 1)), 3),
                    reason,
                )
            )

        if market_pattern == "TREND_CONTINUATION_30S":

            add(
                "Candlestick Engulfing",
                0.55 * pressure +
                0.25 * trend_strength +
                0.20 * volatility,
                "Execution pressure + trend confirmation",
            )

            add(
                "Moving Average Pullback",
                0.45 * trend_strength +
                0.35 * pressure +
                0.20 * volatility,
                "Trend continuation structure",
            )

            add(
                "RSI Momentum",
                0.40 * impulse +
                0.40 * pressure +
                0.20 * trend_strength,
                "Momentum confirmation",
            )

            add(
                "Alligator Strategy",
                0.60 * trend_strength +
                0.20 * pressure +
                0.20 * volatility,
                "Trend alignment",
            )

        add(
            "Reversal Strategy",
            0.50 * rejection +
            0.30 * (1 - impulse) +
            0.20 * noise,
            "Exhaustion detection",
        )

        add(
            "Tweezer Strategy",
            0.70 * rejection +
            0.30 * noise,
            "Rejection structure",
        )

        add(
            "Bollinger Bands",
            0.50 * volatility +
            0.30 * impulse +
            0.20 * (1 - noise),
            "Volatility expansion",
        )

        ranked = sorted(
            scores,
            key=lambda x: x.score,
            reverse=True,
        )

        return {
            "winner": ranked[0].strategy,
            "confidence": ranked[0].score,
            "ranking": [
                {
                    "strategy": x.strategy,
                    "score": x.score,
                    "reason": x.reason,
                }
                for x in ranked
            ],
            "filters": {
                "ADX": adx,
                "ATR7": atr7,
                "trend_strength": trend_strength,
                "volatility": volatility,
            },
        }


def test_competition():

    engine = OTCStrategyCompetition()

    result = engine.rank(
        market_pattern="TREND_CONTINUATION_30S",
        noise=0.288,
        impulse=0.764,
        pressure=0.856,
        rejection=0.25,
        adx=32,
        atr7=0.00012,
    )

    print("\n===== STRATEGY COMPETITION =====")
    print(result)


if __name__ == "__main__":
    test_competition()