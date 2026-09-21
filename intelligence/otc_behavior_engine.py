from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable


@dataclass(frozen=True, slots=True)
class OTCBehaviorProfile:
    """
    Describes current OTC market behavior.

    This class is observational only.
    It does NOT generate BUY/SELL decisions.
    """

    market_mode: str

    noise_score: float
    momentum_score: float
    range_score: float
    impulse_strength: float
    reversal_pressure: float

    samples: int

    up_ticks: int = 0
    down_ticks: int = 0
    same_direction_ratio: float = 0.0

    def as_dict(self) -> dict:
        return {
            "market_mode": self.market_mode,
            "noise_score": round(self.noise_score, 3),
            "momentum_score": round(self.momentum_score, 3),
            "range_score": round(self.range_score, 3),
            "impulse_strength": round(self.impulse_strength, 3),
            "reversal_pressure": round(self.reversal_pressure, 3),
            "samples": self.samples,
            "up_ticks": self.up_ticks,
            "down_ticks": self.down_ticks,
            "same_direction_ratio": round(self.same_direction_ratio, 3),
        }


class OTCBehaviorEngine:
    """
    OTC market behavior analyzer.

    Purpose:
    - measure price behavior
    - detect environment
    - provide context to other systems

    It never decides trades.
    """

    def analyze(
        self,
        prices: Iterable[float],
    ) -> OTCBehaviorProfile:

        values = list(prices)

        if len(values) < 10:
            return OTCBehaviorProfile(
                market_mode="INSUFFICIENT_DATA",
                noise_score=1.0,
                momentum_score=0.0,
                range_score=0.0,
                impulse_strength=0.0,
                reversal_pressure=0.0,
                samples=len(values),
            )


        changes = [
            values[i] - values[i - 1]
            for i in range(1, len(values))
        ]


        abs_changes = [
            abs(x)
            for x in changes
        ]

        up_ticks = sum(
            1 for x in changes if x > 0
        )

        down_ticks = sum(
            1 for x in changes if x < 0
        )

        directional_ticks = up_ticks + down_ticks

        same_direction_ratio = 0.0

        if directional_ticks > 0:
            same_direction_ratio = max(
                up_ticks,
                down_ticks,
            ) / directional_ticks


        total_move = sum(abs_changes)

        if total_move == 0:
            noise = 1.0
        else:
            directional_move = abs(
                values[-1] - values[0]
            )

            efficiency = directional_move / total_move

            # OTC needs internal movement analysis, not only start/end distance.
            # A strong move can return back before the window closes.
            signed_flow = sum(changes)

            positive_flow = sum(
                x for x in changes if x > 0
            )

            negative_flow = sum(
                abs(x) for x in changes if x < 0
            )

            flow_balance = abs(
                positive_flow - negative_flow
            ) / (
                total_move + 1e-9
            )

            noise = 1 - min(
                (efficiency * 0.65)
                + (flow_balance * 0.35),
                1.0,
            )


        avg_move = mean(abs_changes) + 1e-9

        # Detect sustained micro movement.
        movement_intensity = (
            sum(
                1 for x in changes
                if abs(x) > avg_move
            )
            / len(changes)
        )

        momentum = (
            (abs(values[-1] - values[0]) / avg_move) * 0.35
            + movement_intensity * 0.65
        )

        momentum_score = min(
            momentum / 2.5,
            1.0
        )


        volatility = mean(
            abs_changes
        )


        range_width = (
            max(values) - min(values)
        )


        range_score = 0.0

        if range_width > 0:
            range_score = min(
                volatility / range_width,
                1.0
            )


        pressure_balance = abs(
            up_ticks - down_ticks
        ) / max(
            directional_ticks,
            1
        )

        impulse_strength = min(
            (
                momentum_score * 0.45
                + same_direction_ratio * 0.35
                + pressure_balance * 0.20
            )
            * (1 - noise * 0.5),
            1.0,
        )


        reversal_pressure = self._reversal_pressure(
            values
        )


        mode = self._detect_mode(
            momentum_score,
            range_score,
            noise,
        )


        return OTCBehaviorProfile(
            market_mode=mode,
            noise_score=noise,
            momentum_score=momentum_score,
            range_score=range_score,
            impulse_strength=impulse_strength,
            reversal_pressure=reversal_pressure,
            samples=len(values),
            up_ticks=up_ticks,
            down_ticks=down_ticks,
            same_direction_ratio=same_direction_ratio,
        )


    def _detect_mode(
        self,
        momentum: float,
        range_score: float,
        noise: float,
    ) -> str:

        # Noise alone should not classify the OTC market as chaotic.
        # Very short OTC windows naturally contain micro noise.
        # We classify only when noise dominates and directional evidence is weak.

        if (
            noise > 0.85
            and momentum < 0.25
            and range_score < 0.25
        ):
            return "CHAOTIC"

        if momentum > 0.55 and noise < 0.65:
            return "MOMENTUM"

        if range_score > 0.55 and momentum < 0.45:
            return "RANGE"

        if momentum > 0.35:
            return "IMPULSE_TRANSITION"

        return "TRANSITION"



    def _reversal_pressure(
        self,
        prices: list[float],
    ) -> float:

        if len(prices) < 5:
            return 0.0


        recent = prices[-5:]

        first = recent[0]
        last = recent[-1]

        move = last - first

        opposite_moves = 0

        for i in range(1, len(recent)):
            if move > 0 and recent[i] < recent[i - 1]:
                opposite_moves += 1

            elif move < 0 and recent[i] > recent[i - 1]:
                opposite_moves += 1


        return min(
            opposite_moves / 4,
            1.0
        )