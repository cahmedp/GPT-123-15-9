
"""
Candle Quality Validator v4

Market-aware candle quality evaluation.

Changes:
- Wick is not automatically treated as noise.
- Measures price progress versus total path.
- Separates healthy rejection from random movement.
"""

from dataclasses import dataclass


@dataclass
class CandleQualityResult:
    valid: bool
    market_state: str
    quality_score: float
    noise_ratio: float
    trend_strength: float
    directional_efficiency: float
    progress_efficiency: float
    reasons: list


class CandleQualityValidator:

    def validate(self, candles):

        if len(candles) != 10:
            return CandleQualityResult(
                False,
                "INVALID_WINDOW",
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                ["WINDOW_SIZE_ERROR"]
            )

        closes = [c["close"] for c in candles]

        up_moves = 0
        down_moves = 0

        path = 0

        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            path += abs(diff)

            if diff > 0:
                up_moves += 1
            elif diff < 0:
                down_moves += 1

        net_move = abs(closes[-1] - closes[0])

        directional_efficiency = round(
            max(up_moves, down_moves) / 9,
            3
        )

        progress_efficiency = round(
            net_move / (path + 0.001),
            3
        )

        trend_strength = progress_efficiency

        healthy_wicks = 0
        bad_wicks = 0

        for c in candles:
            body = abs(c["close"] - c["open"])
            wick = (
                c["high"] -
                c["low"]
            ) - body

            if wick <= body * 2:
                healthy_wicks += 1
            else:
                bad_wicks += 1

        wick_quality = healthy_wicks / 10

        noise_ratio = round(
            1 - wick_quality,
            3
        )

        quality = round(
            (
                directional_efficiency * 0.3
                +
                trend_strength * 0.3
                +
                progress_efficiency * 0.25
                +
                wick_quality * 0.15
            ),
            3
        )

        reasons = []

        if trend_strength < 0.35:
            reasons.append("WEAK_TREND")

        if progress_efficiency < 0.35:
            reasons.append("LOW_PROGRESS")

        if wick_quality < 0.4:
            reasons.append("BAD_WICK_STRUCTURE")

        valid = (
            quality >= 0.60
            and
            len(reasons) <= 1
        )

        return CandleQualityResult(
            valid,
            "VALID_STRUCTURE" if valid else "NOISY_STRUCTURE",
            quality,
            noise_ratio,
            trend_strength,
            directional_efficiency,
            progress_efficiency,
            reasons
        )
