from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass, field
from typing import Any, Optional

from config import CONFIG
from simulation.world_model import WorldModelSnapshot


@dataclass(frozen=True, slots=True)
class ScenarioPath:
    scenario_id: int
    scenario_type: str

    direction: str
    probability_weight: float

    projected_move_atr: float
    projected_volatility: float
    projected_noise: float

    horizon_candles: int

    survived: bool
    quality: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_type": self.scenario_type,
            "direction": self.direction,
            "probability_weight": self.probability_weight,
            "projected_move_atr": self.projected_move_atr,
            "projected_volatility": self.projected_volatility,
            "projected_noise": self.projected_noise,
            "horizon_candles": self.horizon_candles,
            "survived": self.survived,
            "quality": self.quality,
        }


@dataclass(frozen=True, slots=True)
class ScenarioSimulationResult:
    timestamp: float
    asset: str
    price: float

    scenarios_run: int
    horizon_candles: int

    bullish_probability: float
    bearish_probability: float
    sideways_probability: float
    failure_probability: float

    expected_directional_score: float
    expected_move_atr: float

    simulation_confidence: float
    scenario_disagreement: float

    dominant_scenario: str
    dominant_direction: str

    usable_for_fusion: bool

    scenarios: tuple[ScenarioPath, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "asset": self.asset,
            "price": self.price,
            "scenarios_run": self.scenarios_run,
            "horizon_candles": self.horizon_candles,
            "bullish_probability": self.bullish_probability,
            "bearish_probability": self.bearish_probability,
            "sideways_probability": self.sideways_probability,
            "failure_probability": self.failure_probability,
            "expected_directional_score": self.expected_directional_score,
            "expected_move_atr": self.expected_move_atr,
            "simulation_confidence": self.simulation_confidence,
            "scenario_disagreement": self.scenario_disagreement,
            "dominant_scenario": self.dominant_scenario,
            "dominant_direction": self.dominant_direction,
            "usable_for_fusion": self.usable_for_fusion,
            "scenarios": [
                scenario.as_dict()
                for scenario in self.scenarios
            ],
            "reasons": list(self.reasons),
        }


class ScenarioEngine:
    """
    Short-horizon scenario simulator.

    It consumes WorldModelSnapshot and creates multiple possible future paths.

    The simulation models:
        - directional continuation,
        - reversal,
        - range persistence,
        - expansion,
        - analytical failure / unreliable conditions.

    Important:
        - Results are model estimates, not guaranteed market probabilities.
        - Simulation uses only information available at the current timestamp.
        - The random generator is deterministically seeded from the current
          world state so replay/backtest produces repeatable results.
        - No order execution exists in this module.
    """

    def __init__(
        self,
        max_scenarios: int = CONFIG.WORLD_MODEL_MAX_SCENARIOS,
        horizon_candles: int = CONFIG.WORLD_MODEL_HORIZON_CANDLES,
    ) -> None:
        if max_scenarios <= 0:
            raise ValueError(
                "max_scenarios must be greater than zero."
            )

        if horizon_candles <= 0:
            raise ValueError(
                "horizon_candles must be greater than zero."
            )

        self.max_scenarios = int(max_scenarios)
        self.horizon_candles = int(horizon_candles)

    def simulate(
        self,
        world: WorldModelSnapshot,
        *,
        scenario_count: Optional[int] = None,
    ) -> ScenarioSimulationResult:

        count = int(
            scenario_count
            if scenario_count is not None
            else self.max_scenarios
        )

        count = min(
            max(count, 1),
            self.max_scenarios,
        )

        state = world.state

        if not world.simulation_allowed:
            return ScenarioSimulationResult(
                timestamp=state.timestamp,
                asset=state.asset,
                price=state.price,

                scenarios_run=0,
                horizon_candles=self.horizon_candles,

                bullish_probability=0.0,
                bearish_probability=0.0,
                sideways_probability=0.0,
                failure_probability=1.0,

                expected_directional_score=0.0,
                expected_move_atr=0.0,

                simulation_confidence=0.0,
                scenario_disagreement=1.0,

                dominant_scenario="FAILURE",
                dominant_direction="WAIT",

                usable_for_fusion=False,

                scenarios=tuple(),
                reasons=(
                    "world model did not allow scenario simulation",
                ),
            )

        rng = random.Random(
            self._deterministic_seed(world)
        )

        priors = self._scenario_priors(
            world
        )

        scenarios: list[ScenarioPath] = []

        for scenario_id in range(
            1,
            count + 1,
        ):
            scenario_type = self._sample_type(
                rng=rng,
                priors=priors,
            )

            scenario = self._simulate_path(
                scenario_id=scenario_id,
                scenario_type=scenario_type,
                world=world,
                rng=rng,
            )

            scenarios.append(
                scenario
            )

        (
            bullish_probability,
            bearish_probability,
            sideways_probability,
            failure_probability,
        ) = self._aggregate_probabilities(
            scenarios
        )

        expected_directional_score = self._clip(
            bullish_probability
            - bearish_probability,
            -1.0,
            1.0,
        )

        expected_move_atr = self._weighted_expected_move(
            scenarios
        )

        disagreement = self._scenario_disagreement(
            bullish_probability=bullish_probability,
            bearish_probability=bearish_probability,
            sideways_probability=sideways_probability,
            failure_probability=failure_probability,
        )

        confidence = self._simulation_confidence(
            world=world,
            scenarios=scenarios,
            disagreement=disagreement,
            failure_probability=failure_probability,
        )

        dominant_scenario = self._dominant_scenario(
            scenarios
        )

        dominant_direction = self._dominant_direction(
            bullish_probability=bullish_probability,
            bearish_probability=bearish_probability,
            sideways_probability=sideways_probability,
            failure_probability=failure_probability,
            confidence=confidence,
        )

        usable_for_fusion = self._usable_for_fusion(
            world=world,
            confidence=confidence,
            disagreement=disagreement,
            failure_probability=failure_probability,
        )

        reasons = self._build_reasons(
            world=world,
            count=count,
            bullish_probability=bullish_probability,
            bearish_probability=bearish_probability,
            sideways_probability=sideways_probability,
            failure_probability=failure_probability,
            expected_directional_score=expected_directional_score,
            expected_move_atr=expected_move_atr,
            confidence=confidence,
            disagreement=disagreement,
            dominant_scenario=dominant_scenario,
            dominant_direction=dominant_direction,
            usable_for_fusion=usable_for_fusion,
        )

        # Keep a bounded representative sample for UI/reporting.
        visible_scenarios = tuple(
            sorted(
                scenarios,
                key=lambda item: (
                    item.quality,
                    item.probability_weight,
                ),
                reverse=True,
            )[:50]
        )

        return ScenarioSimulationResult(
            timestamp=float(
                state.timestamp
            ),
            asset=state.asset,
            price=float(
                state.price
            ),

            scenarios_run=count,
            horizon_candles=self.horizon_candles,

            bullish_probability=float(
                bullish_probability
            ),
            bearish_probability=float(
                bearish_probability
            ),
            sideways_probability=float(
                sideways_probability
            ),
            failure_probability=float(
                failure_probability
            ),

            expected_directional_score=float(
                expected_directional_score
            ),
            expected_move_atr=float(
                expected_move_atr
            ),

            simulation_confidence=float(
                confidence
            ),
            scenario_disagreement=float(
                disagreement
            ),

            dominant_scenario=dominant_scenario,
            dominant_direction=dominant_direction,

            usable_for_fusion=usable_for_fusion,

            scenarios=visible_scenarios,
            reasons=tuple(reasons),
        )

    def _simulate_path(
        self,
        *,
        scenario_id: int,
        scenario_type: str,
        world: WorldModelSnapshot,
        rng: random.Random,
    ) -> ScenarioPath:
        state = world.state

        base_direction = (
            1.0
            if state.directional_bias > 0
            else -1.0
            if state.directional_bias < 0
            else 0.0
        )

        directional_strength = self._clip01(
            state.directional_strength
        )

        noise = self._clip01(
            state.noise
        )

        conflict = self._clip01(
            state.conflict
        )

        expansion = self._clip01(
            state.expansion
        )

        compression = self._clip01(
            state.compression
        )

        random_variation = rng.uniform(
            -0.18,
            0.18,
        )

        if scenario_type == "CONTINUATION":
            direction_value = (
                base_direction
                if base_direction != 0
                else (
                    1.0
                    if rng.random() >= 0.5
                    else -1.0
                )
            )

            move = (
                direction_value
                * (
                    0.45
                    + 1.10
                    * directional_strength
                    + 0.45
                    * expansion
                )
            )

            projected_volatility = self._clip01(
                0.35
                + 0.45
                * expansion
                + 0.20
                * noise
            )

        elif scenario_type == "REVERSAL":
            direction_value = (
                -base_direction
                if base_direction != 0
                else (
                    1.0
                    if rng.random() >= 0.5
                    else -1.0
                )
            )

            move = (
                direction_value
                * (
                    0.30
                    + 0.70
                    * max(
                        world.reversal_prior,
                        state.conflict,
                    )
                )
            )

            projected_volatility = self._clip01(
                0.45
                + 0.25
                * state.conflict
                + 0.25
                * noise
            )

        elif scenario_type == "RANGE":
            direction_value = 0.0

            move = (
                random_variation
                * (
                    0.20
                    + 0.50
                    * compression
                )
            )

            projected_volatility = self._clip01(
                0.20
                + 0.30
                * compression
                + 0.20
                * noise
            )

        elif scenario_type == "EXPANSION":
            direction_value = (
                base_direction
                if base_direction != 0
                else (
                    1.0
                    if rng.random() >= 0.5
                    else -1.0
                )
            )

            # Expansion may follow the dominant direction, but conflict/noise
            # gives a bounded probability of an opposite release.
            flip_probability = self._clip01(
                0.15
                + 0.35
                * conflict
                + 0.20
                * noise
            )

            if rng.random() < flip_probability:
                direction_value *= -1.0

            move = (
                direction_value
                * (
                    0.75
                    + 1.25
                    * expansion
                    + 0.40
                    * compression
                )
            )

            projected_volatility = self._clip01(
                0.60
                + 0.35
                * expansion
            )

        else:
            direction_value = 0.0

            move = random_variation * 0.25

            projected_volatility = self._clip01(
                0.60
                + 0.35
                * noise
            )

        move += random_variation

        projected_noise = self._clip01(
            noise
            + rng.uniform(
                -0.10,
                0.10,
            )
            + 0.15
            * conflict
        )

        scenario_weight = self._scenario_weight(
            scenario_type=scenario_type,
            world=world,
        )

        failure_chance = self._clip01(
            world.failure_prior
            * (
                0.65
                + 0.35
                * projected_noise
            )
        )

        survived = (
            scenario_type != "FAILURE"
            and rng.random()
            > failure_chance
        )

        if scenario_type == "FAILURE":
            survived = False

        quality = self._clip01(
            (
                world.evidence_quality
                * scenario_weight
            )
            * (
                1.0
                - 0.55
                * projected_noise
            )
            * (
                1.0
                - 0.35
                * state.conflict
            )
        )

        if not survived:
            quality *= 0.30

        direction = self._direction_from_move(
            move=move,
            survived=survived,
        )

        return ScenarioPath(
            scenario_id=scenario_id,
            scenario_type=scenario_type,
            direction=direction,
            probability_weight=float(
                scenario_weight
            ),
            projected_move_atr=float(
                move
            ),
            projected_volatility=float(
                projected_volatility
            ),
            projected_noise=float(
                projected_noise
            ),
            horizon_candles=self.horizon_candles,
            survived=bool(
                survived
            ),
            quality=float(
                quality
            ),
        )

    @staticmethod
    def _scenario_priors(
        world: WorldModelSnapshot,
    ) -> dict[str, float]:
        priors = {
            "CONTINUATION": max(
                float(
                    world.continuation_prior
                ),
                0.0,
            ),
            "REVERSAL": max(
                float(
                    world.reversal_prior
                ),
                0.0,
            ),
            "RANGE": max(
                float(
                    world.range_prior
                ),
                0.0,
            ),
            "EXPANSION": max(
                float(
                    world.expansion_prior
                ),
                0.0,
            ),
            "FAILURE": max(
                float(
                    world.failure_prior
                ),
                0.0,
            ),
        }

        total = sum(
            priors.values()
        )

        if total <= 1e-12:
            return {
                key: 0.20
                for key in priors
            }

        return {
            key: value / total
            for key, value
            in priors.items()
        }

    @staticmethod
    def _sample_type(
        *,
        rng: random.Random,
        priors: dict[str, float],
    ) -> str:
        target = rng.random()
        cumulative = 0.0

        for scenario_type, weight in priors.items():
            cumulative += weight

            if target <= cumulative:
                return scenario_type

        return "FAILURE"

    @staticmethod
    def _scenario_weight(
        *,
        scenario_type: str,
        world: WorldModelSnapshot,
    ) -> float:
        mapping = {
            "CONTINUATION": world.continuation_prior,
            "REVERSAL": world.reversal_prior,
            "RANGE": world.range_prior,
            "EXPANSION": world.expansion_prior,
            "FAILURE": world.failure_prior,
        }

        return ScenarioEngine._clip01(
            mapping.get(
                scenario_type,
                0.0,
            )
        )

    @classmethod
    def _aggregate_probabilities(
        cls,
        scenarios: list[ScenarioPath],
    ) -> tuple[
        float,
        float,
        float,
        float,
    ]:
        if not scenarios:
            return (
                0.0,
                0.0,
                0.0,
                1.0,
            )

        bullish = 0.0
        bearish = 0.0
        sideways = 0.0
        failure = 0.0

        total = 0.0

        for scenario in scenarios:
            weight = max(
                scenario.probability_weight
                * max(
                    scenario.quality,
                    0.05,
                ),
                1e-9,
            )

            total += weight

            if not scenario.survived:
                failure += weight

            elif scenario.direction == "BULLISH":
                bullish += weight

            elif scenario.direction == "BEARISH":
                bearish += weight

            else:
                sideways += weight

        if total <= 1e-12:
            return (
                0.0,
                0.0,
                0.0,
                1.0,
            )

        return (
            cls._clip01(
                bullish / total
            ),
            cls._clip01(
                bearish / total
            ),
            cls._clip01(
                sideways / total
            ),
            cls._clip01(
                failure / total
            ),
        )

    @staticmethod
    def _weighted_expected_move(
        scenarios: list[ScenarioPath],
    ) -> float:
        if not scenarios:
            return 0.0

        numerator = 0.0
        denominator = 0.0

        for scenario in scenarios:
            if not scenario.survived:
                continue

            weight = max(
                scenario.quality
                * scenario.probability_weight,
                1e-9,
            )

            numerator += (
                scenario.projected_move_atr
                * weight
            )

            denominator += weight

        if denominator <= 1e-12:
            return 0.0

        return float(
            numerator / denominator
        )

    @classmethod
    def _scenario_disagreement(
        cls,
        *,
        bullish_probability: float,
        bearish_probability: float,
        sideways_probability: float,
        failure_probability: float,
    ) -> float:

        values = (
            bullish_probability,
            bearish_probability,
            sideways_probability,
            failure_probability,
        )

        max_probability = max(
            values
        )

        # 0 when one outcome dominates.
        # Approaches 1 when outcomes are evenly distributed.
        return cls._clip01(
            (
                1.0
                - max_probability
            )
            / 0.75
        )

    @classmethod
    def _simulation_confidence(
        cls,
        *,
        world: WorldModelSnapshot,
        scenarios: list[ScenarioPath],
        disagreement: float,
        failure_probability: float,
    ) -> float:
        if not scenarios:
            return 0.0

        average_quality = sum(
            scenario.quality
            for scenario in scenarios
        ) / len(
            scenarios
        )

        survived_ratio = sum(
            1
            for scenario in scenarios
            if scenario.survived
        ) / len(
            scenarios
        )

        sample_factor = cls._clip01(
            len(scenarios)
            / max(
                CONFIG.WORLD_MODEL_MAX_SCENARIOS,
                1,
            )
        )

        return cls._clip01(
            (
                0.35
                * world.evidence_quality
                + 0.25
                * average_quality
                + 0.20
                * survived_ratio
                + 0.10
                * sample_factor
                + 0.10
                * (
                    1.0
                    - disagreement
                )
            )
            * (
                1.0
                - 0.60
                * failure_probability
            )
        )

    @staticmethod
    def _dominant_scenario(
        scenarios: list[ScenarioPath],
    ) -> str:
        if not scenarios:
            return "FAILURE"

        weights: dict[
            str,
            float,
        ] = {}

        for scenario in scenarios:
            value = (
                scenario.probability_weight
                * max(
                    scenario.quality,
                    0.05,
                )
            )

            weights[
                scenario.scenario_type
            ] = (
                weights.get(
                    scenario.scenario_type,
                    0.0,
                )
                + value
            )

        return max(
            weights,
            key=weights.get,
        )

    @staticmethod
    def _dominant_direction(
        *,
        bullish_probability: float,
        bearish_probability: float,
        sideways_probability: float,
        failure_probability: float,
        confidence: float,
    ) -> str:
        if confidence < 0.35:
            return "WAIT"

        values = {
            "BULLISH": bullish_probability,
            "BEARISH": bearish_probability,
            "WAIT": max(
                sideways_probability,
                failure_probability,
            ),
        }

        return max(
            values,
            key=values.get,
        )

    @staticmethod
    def _usable_for_fusion(
        *,
        world: WorldModelSnapshot,
        confidence: float,
        disagreement: float,
        failure_probability: float,
    ) -> bool:
        if not world.simulation_allowed:
            return False

        if confidence < 0.35:
            return False

        if disagreement > 0.75:
            return False

        if failure_probability > 0.55:
            return False

        return True

    @staticmethod
    def _direction_from_move(
        *,
        move: float,
        survived: bool,
    ) -> str:
        if not survived:
            return "WAIT"

        if move >= 0.15:
            return "BULLISH"

        if move <= -0.15:
            return "BEARISH"

        return "SIDEWAYS"

    @staticmethod
    def _deterministic_seed(
        world: WorldModelSnapshot,
    ) -> int:
        payload = (
            f"{world.state.asset}|"
            f"{world.state.timestamp:.6f}|"
            f"{world.state.price:.8f}|"
            f"{world.state.directional_bias:.8f}|"
            f"{world.evidence_quality:.8f}"
        )

        digest = hashlib.sha256(
            payload.encode(
                "utf-8"
            )
        ).digest()

        return int.from_bytes(
            digest[:8],
            "big",
            signed=False,
        )

    @staticmethod
    def _build_reasons(
        *,
        world: WorldModelSnapshot,
        count: int,
        bullish_probability: float,
        bearish_probability: float,
        sideways_probability: float,
        failure_probability: float,
        expected_directional_score: float,
        expected_move_atr: float,
        confidence: float,
        disagreement: float,
        dominant_scenario: str,
        dominant_direction: str,
        usable_for_fusion: bool,
    ) -> list[str]:
        reasons: list[str] = [
            f"{count} deterministic short-horizon scenarios were simulated",
            f"dominant scenario: {dominant_scenario.lower()}",
            f"dominant direction: {dominant_direction.lower()}",
        ]

        if bullish_probability >= 0.45:
            reasons.append(
                "simulation distribution leans bullish"
            )

        if bearish_probability >= 0.45:
            reasons.append(
                "simulation distribution leans bearish"
            )

        if sideways_probability >= 0.40:
            reasons.append(
                "sideways/range scenarios are materially represented"
            )

        if failure_probability >= 0.35:
            reasons.append(
                "model-failure / unreliable scenarios are elevated"
            )

        if abs(
            expected_directional_score
        ) < 0.15:
            reasons.append(
                "expected directional edge is weak"
            )

        if abs(
            expected_move_atr
        ) >= 1.0:
            reasons.append(
                "simulated move magnitude is large relative to ATR"
            )

        if disagreement >= 0.60:
            reasons.append(
                "simulated futures materially disagree"
            )

        reasons.append(
            f"simulation confidence={confidence:.2f}"
        )

        reasons.append(
            f"world evidence quality={world.evidence_quality:.2f}"
        )

        if usable_for_fusion:
            reasons.append(
                "simulation result is suitable for final decision fusion"
            )
        else:
            reasons.append(
                "simulation should not materially influence final decision"
            )

        return reasons

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
