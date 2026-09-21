"""
OTC Strategy Pattern Agent Test - 30s Optimized

Purpose:
Classify 30 second OTC microstructure and map it to strategy families.

Timeframe hierarchy:
5M  = Context
1M  = Setup
30S = Execution trigger

Important:
This is a testing layer only.
It does not execute trades.
"""

from dataclasses import dataclass


@dataclass
class PatternDecision:
    pattern: str
    strategies: list[str]
    confidence: float
    reason: str


class OTCStrategyPatternAgent:

    def analyze(
        self,
        context_5m: str,
        setup_1m: str,
        noise: float,
        impulse: float,
        pressure: float,
        rejection: float,
        compression: float,
        reversal_pressure: float,
    ) -> PatternDecision:

        # 30s sensitivity profile
        # Avoid slow timeframe parameters.
        clean_market = noise < 0.45
        strong_execution = pressure >= 0.70
        breakout_energy = compression >= 0.65 and impulse >= 0.65

        # Custom OTC microstructure patterns first

        if breakout_energy:
            return PatternDecision(
                "OTC_COMPRESSION_EXPANSION",
                [
                    "Level Breakout",
                    "Bollinger Bands Strategy",
                    "Momentum Expansion"
                ],
                0.80,
                "Compression released with execution impulse"
            )

        if (
            context_5m == "BULLISH"
            and setup_1m == "PULLBACK"
            and strong_execution
            and clean_market
        ):
            return PatternDecision(
                "TREND_CONTINUATION_30S",
                [
                    "Moving Averages Strategy",
                    "Candlestick Engulfing",
                    "RSI Trading Strategy",
                    "Alligator Strategy"
                ],
                0.82,
                "Higher timeframe trend + lower timeframe confirmation"
            )

        if (
            context_5m == "BEARISH"
            and setup_1m == "PULLBACK"
            and pressure < 0.45
        ):
            return PatternDecision(
                "COUNTER_TREND_WARNING",
                [
                    "Reversal Strategy",
                    "Tweezer Strategy",
                    "Squat Candlestick Strategy"
                ],
                0.72,
                "Execution conflicts with 5M context"
            )

        if (
            reversal_pressure >= 0.60
            or rejection >= 0.60
        ):
            return PatternDecision(
                "REVERSAL_STRUCTURE",
                [
                    "Reversal Strategy",
                    "Tweezer Strategy",
                    "Candlestick Engulfing",
                    "Bollinger Bands Strategy"
                ],
                0.76,
                "Exhaustion and rejection detected"
            )

        if noise >= 0.80:
            return PatternDecision(
                "NO_EDGE_RANGE",
                [
                    "Bollinger Range",
                    "Support Resistance"
                ],
                0.60,
                "Market is not clean for execution"
            )

        return PatternDecision(
            "UNKNOWN",
            [],
            0.30,
            "Insufficient structure"
        )


if __name__ == "__main__":

    agent = OTCStrategyPatternAgent()

    result = agent.analyze(
        context_5m="BULLISH",
        setup_1m="PULLBACK",
        noise=0.288,
        impulse=0.764,
        pressure=0.856,
        rejection=0.25,
        compression=0.20,
        reversal_pressure=0.25,
    )

    print(result)
