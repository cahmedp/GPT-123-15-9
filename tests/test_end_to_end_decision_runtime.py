# ============================================================
# START PART 1/3
#
# tests/test_end_to_end_decision_runtime.py
#
# Professional End-To-End Decision Runtime Validation
#
# ============================================================

from __future__ import annotations

import math
import time

from dataclasses import dataclass
from typing import Any, Callable, Mapping, TypeVar


from config import CONFIG
from core.orchestrator import Analyst
from data.pocket_connector import HistoricalCandle


# ============================================================
# GENERIC TYPES
# ============================================================

T = TypeVar("T")


# ============================================================
# TEST RESULT CONTRACTS
# ============================================================


@dataclass(slots=True)
class StageResult:
    """
    Execution result for one integration-test stage.
    """

    name: str
    passed: bool
    duration_ms: float
    details: str = ""


@dataclass(slots=True)
class RuntimeConsensus:
    """
    Minimal consensus contract required by FullDecisionRuntime.
    """

    status: str
    confidence: float


# ============================================================
# NUMERIC SAFETY
# ============================================================


def clip01(
    value: float,
) -> float:
    """
    Clamp a numeric value into [0.0, 1.0].
    """

    return min(
        max(
            float(value),
            0.0,
        ),
        1.0,
    )


# ============================================================
# STAGE EXECUTION WRAPPER
# ============================================================


def execute_stage(
    *,
    results: list[StageResult],
    name: str,
    operation: Callable[[], T],
    details: Callable[[T], str] | None = None,
) -> T:
    """
    Executes one test stage.

    Provides:
    - timing,
    - PASS / FAIL visibility,
    - exact failing stage,
    - original exception propagation.

    It does not hide real failures.
    """

    started = time.perf_counter()

    try:
        value = operation()

    except Exception as exc:
        duration_ms = (
            time.perf_counter()
            - started
        ) * 1000.0

        results.append(
            StageResult(
                name=name,
                passed=False,
                duration_ms=duration_ms,
                details=(
                    f"{type(exc).__name__}: {exc}"
                ),
            )
        )

        print(
            f"[FAIL] {name} | "
            f"{duration_ms:.2f} ms | "
            f"{type(exc).__name__}: {exc}"
        )

        raise

    duration_ms = (
        time.perf_counter()
        - started
    ) * 1000.0

    detail_text = (
        details(value)
        if details is not None
        else "OK"
    )

    results.append(
        StageResult(
            name=name,
            passed=True,
            duration_ms=duration_ms,
            details=detail_text,
        )
    )

    print(
        f"[PASS] {name} | "
        f"{duration_ms:.2f} ms | "
        f"{detail_text}"
    )

    return value


# ============================================================
# SYNTHETIC MARKET GENERATOR
# ============================================================


def build_fake_candles(
    count: int = 360,
) -> list[HistoricalCandle]:
    """
    Generate deterministic 30-second GBPUSD_OTC candles.

    Important properties:
    - positive Unix timestamps,
    - strictly increasing timestamps,
    - valid OHLC relationships,
    - enough history for 30s / 1m / 5m analysis,
    - deterministic behavior,
    - no network dependency.

    The generated data contains:
    - a mild upward drift,
    - controlled cyclic movement,
    - changing candle bodies,
    - realistic high/low envelopes.

    It is intended for pipeline validation,
    not strategy-performance testing.
    """

    if count < 120:
        raise ValueError(
            "Synthetic history requires at least 120 base candles."
        )

    timeframe = int(
        CONFIG.BASE_TIMEFRAME_SECONDS
    )

    if timeframe <= 0:
        raise ValueError(
            "BASE_TIMEFRAME_SECONDS must be positive."
        )

    # Use the most recently completed timeframe boundary.
    end_timestamp = (
        int(time.time() // timeframe)
        * timeframe
        - timeframe
    )

    start_timestamp = (
        end_timestamp
        - ((count - 1) * timeframe)
    )

    if start_timestamp <= 0:
        raise ValueError(
            "Synthetic start timestamp must be positive."
        )

    candles: list[HistoricalCandle] = []

    base_price = 1.10000

    previous_close = base_price

    for index in range(count):
        timestamp = float(
            start_timestamp
            + (index * timeframe)
        )

        # Long-term deterministic drift.
        drift = (
            index
            * 0.0000025
        )

        # Smooth micro-cycle.
        wave = (
            math.sin(
                index / 7.0
            )
            * 0.000035
        )

        # Slower secondary structure.
        slow_wave = (
            math.sin(
                index / 31.0
            )
            * 0.000055
        )

        target_close = (
            base_price
            + drift
            + wave
            + slow_wave
        )

        open_price = (
            previous_close
        )

        close_price = float(
            target_close
        )

        body_high = max(
            open_price,
            close_price,
        )

        body_low = min(
            open_price,
            close_price,
        )

        wick_size = (
            0.000025
            +
            abs(
                math.sin(
                    index / 5.0
                )
            )
            * 0.000015
        )

        high_price = (
            body_high
            + wick_size
        )

        low_price = (
            body_low
            - wick_size
        )

        candle = HistoricalCandle(
            asset=CONFIG.PAIR,
            timestamp=timestamp,
            timeframe_seconds=timeframe,
            open=float(open_price),
            high=float(high_price),
            low=float(low_price),
            close=float(close_price),
        )

        candles.append(
            candle
        )

        previous_close = (
            close_price
        )

    return candles


# ============================================================
# CANDLE ACCESS ADAPTER
# ============================================================


def candles_for_timeframe(
    analyst: Analyst,
    timeframe: int,
) -> list[HistoricalCandle]:
    """
    Retrieve candles directly from DataManager.

    The integration test intentionally does not depend on
    Analyst._candles(), keeping the test independent from
    private orchestration helpers.
    """

    candles = [
        candle
        for candle
        in analyst.data.latest_candles()
        if (
            candle.timeframe_seconds
            == timeframe
        )
    ]

    candles.sort(
        key=lambda candle:
        float(candle.timestamp)
    )

    unique: dict[
        float,
        HistoricalCandle,
    ] = {
        float(candle.timestamp):
            candle
        for candle
        in candles
    }

    return [
        unique[timestamp]
        for timestamp
        in sorted(unique)
    ]


# ============================================================
# PATTERN TAG ADAPTER
# ============================================================


def build_pattern_tags(
    patterns: Mapping[int, Any],
) -> tuple[str, ...]:
    """
    Build knowledge tags locally.

    This removes the test dependency on
    Analyst._pattern_tags().
    """

    tags: set[str] = set()

    signal_names = (
        "compression",
        "wick_cluster",
        "rejection",
        "fake_break",
        "breakout",
        "breakout_retest",
        "expansion",
    )

    labels = {
        int(
            CONFIG.BASE_TIMEFRAME_SECONDS
        ): "30s",

        int(
            CONFIG.TIMEFRAME_1M_SECONDS
        ): "1m",

        int(
            CONFIG.TIMEFRAME_5M_SECONDS
        ): "5m",
    }

    for timeframe, snapshot in (
        patterns.items()
    ):
        label = labels.get(
            int(timeframe),
            f"{timeframe}s",
        )

        for signal_name in (
            signal_names
        ):
            signal = getattr(
                snapshot,
                signal_name,
                None,
            )

            if signal is None:
                continue

            tags.add(
                signal_name
            )

            tags.add(
                f"{label}:{signal_name}"
            )

            direction = getattr(
                signal,
                "direction",
                None,
            )

            if direction is not None:
                tags.add(
                    f"{signal_name}:"
                    f"{str(direction).lower()}"
                )

    return tuple(
        sorted(tags)
    )


# ============================================================
# FULL RUNTIME ADAPTERS
#
# These reproduce only the inputs required by FullDecisionRuntime.
# The test no longer depends on Analyst private helper methods.
# ============================================================


def build_runtime_consensus(
    debate: Any,
) -> RuntimeConsensus:
    """
    Normalize agent debate into runtime consensus.
    """

    confidence = clip01(
        float(
            getattr(
                debate,
                "consensus_confidence",
                0.0,
            )
            or 0.0
        )
    )

    disagreement = clip01(
        float(
            getattr(
                debate,
                "disagreement_score",
                1.0,
            )
            or 1.0
        )
    )

    uncertainty = clip01(
        float(
            getattr(
                debate,
                "uncertainty_score",
                1.0,
            )
            or 1.0
        )
    )

    direction = str(
        getattr(
            debate,
            "consensus_direction",
            "WAIT",
        )
        or "WAIT"
    ).upper()

    reliable = (
        direction in {
            "BULLISH",
            "BEARISH",
        }
        and confidence >= 0.70
        and disagreement <= 0.40
        and uncertainty <= 0.60
    )

    return RuntimeConsensus(
        status=(
            "RELIABLE_CONSENSUS"
            if reliable
            else "WEAK_CONSENSUS"
        ),
        confidence=confidence,
    )


def calculate_market_multiplier(
    market: Any,
) -> float:
    """
    Convert current market quality into a runtime multiplier.
    """

    quality = clip01(
        float(
            getattr(
                market,
                "market_quality",
                0.5,
            )
            or 0.5
        )
    )

    return max(
        quality,
        0.30,
    )


def calculate_knowledge_reliability(
    knowledge_support: Mapping[str, Any],
) -> float:
    """
    Convert historical knowledge support
    into a bounded reliability factor.
    """

    count = int(
        knowledge_support.get(
            "count",
            0,
        )
        or 0
    )

    success_rate = clip01(
        float(
            knowledge_support.get(
                "success_rate",
                0.70,
            )
            or 0.70
        )
    )

    sample_factor = min(
        count / 20.0,
        1.0,
    )

    reliability = (
        0.55
        + success_rate * 0.30
        + sample_factor * 0.15
    )

    return min(
        max(
            reliability,
            0.55,
        ),
        1.0,
    )


def calculate_calibration_factor(
    calibrated: Any,
) -> float:
    """
    Derive runtime calibration modifier.
    """

    confidence = clip01(
        float(
            getattr(
                calibrated,
                "calibrated_confidence",
                0.0,
            )
            or 0.0
        )
    )

    if confidence <= 0.0:
        return 1.0

    return min(
        max(
            confidence / 0.85,
            0.75,
        ),
        1.05,
    )


def detect_market_mode(
    *,
    market: Any,
    regime: Any,
) -> str:
    """
    Determine dynamic threshold mode for the test.
    """

    quality = clip01(
        float(
            getattr(
                market,
                "market_quality",
                0.5,
            )
            or 0.5
        )
    )

    noise = clip01(
        float(
            getattr(
                regime,
                "noise_strength",
                0.0,
            )
            or 0.0
        )
    )

    if (
        noise >= 0.70
        or quality < 0.50
    ):
        return "DEFENSIVE"

    if (
        noise >= 0.45
        or quality < 0.70
    ):
        return "CAUTIOUS"

    return "NORMAL"


def calculate_data_health(
    market: Any,
) -> float:
    """
    The synthetic stream is assumed fresh.

    Data health therefore combines perfect stream freshness
    with the market engine's own quality assessment.
    """

    market_quality = clip01(
        float(
            getattr(
                market,
                "market_quality",
                0.5,
            )
            or 0.5
        )
    )

    return clip01(
        (
            market_quality
            + 1.0
        )
        / 2.0
    )


def validate_microstructure(
    regime: Any,
) -> bool:
    """
    Basic runtime microstructure validity check.
    """

    noise = clip01(
        float(
            getattr(
                regime,
                "noise_strength",
                0.0,
            )
            or 0.0
        )
    )

    return (
        noise < 0.80
    )


# ============================================================
# TEST ENTRY POINT
# ============================================================


def run() -> None:
    """
    Execute the complete synthetic decision pipeline.
    """

    print(
        "\n"
        + "=" * 72
    )

    print(
        "PROFESSIONAL END-TO-END DECISION RUNTIME TEST"
    )

    print(
        "=" * 72
    )

    results: list[
        StageResult
    ] = []


    # ========================================================
    # STAGE 1
    # ANALYST INITIALIZATION
    # ========================================================

    analyst = execute_stage(
        results=results,
        name="Analyst Initialization",
        operation=Analyst,
        details=lambda _: (
            "Runtime components initialized"
        ),
    )


    # ========================================================
    # STAGE 2
    # SYNTHETIC MARKET GENERATION
    # ========================================================

    synthetic_candles = execute_stage(
        results=results,
        name="Synthetic Market Generation",
        operation=lambda: (
            build_fake_candles(
                count=360
            )
        ),
        details=lambda candles: (
            f"{len(candles)} base candles generated"
        ),
    )


    # ========================================================
    # STAGE 3
    # CANDLE BUILDER / INGESTION
    # ========================================================

    def ingest_candles() -> int:
        emitted = (
            analyst.candle_builder
            .seed_base_candles(
                synthetic_candles
            )
        )

        stored = 0

        for timeframe_candles in (
            emitted.values()
        ):
            analyst.data.add_candles(
                timeframe_candles
            )

            stored += len(
                timeframe_candles
            )

        if stored <= 0:
            raise AssertionError(
                "CandleBuilder emitted no candles."
            )

        return stored


    stored_count = execute_stage(
        results=results,
        name="Candle Builder + Data Ingestion",
        operation=ingest_candles,
        details=lambda count: (
            f"{count} candles stored across timeframes"
        ),
    )


    # ========================================================
    # PART 1 ENDS HERE
    # PART 2 CONTINUES INSIDE run()
    # ========================================================


# ============================================================
# END PART 1/3
# Next: Market Intelligence -> Simulation
# ============================================================
# ============================================================
# START PART 2/3
#
# Intelligence Pipeline Execution
#
# Market Intelligence
# Pattern Engine
# Regime
# Agents
# World Model
# Simulation
#
# ============================================================



    # ========================================================
    # STAGE 4
    # MARKET INTELLIGENCE
    # ========================================================


    candles_by_timeframe = execute_stage(
        results=results,
        name="Multi Timeframe Candle Preparation",
        operation=lambda: {

            int(CONFIG.BASE_TIMEFRAME_SECONDS):
                candles_for_timeframe(
                    analyst,
                    int(
                        CONFIG.BASE_TIMEFRAME_SECONDS
                    ),
                ),

            int(CONFIG.TIMEFRAME_1M_SECONDS):
                candles_for_timeframe(
                    analyst,
                    int(
                        CONFIG.TIMEFRAME_1M_SECONDS
                    ),
                ),

            int(CONFIG.TIMEFRAME_5M_SECONDS):
                candles_for_timeframe(
                    analyst,
                    int(
                        CONFIG.TIMEFRAME_5M_SECONDS
                    ),
                ),

        },
        details=lambda data: (
            " | ".join(
                [
                    f"{key}s={len(value)}"
                    for key, value
                    in data.items()
                ]
            )
        ),
    )



    market = execute_stage(
        results=results,
        name="Market Intelligence",
        operation=lambda: (
            analyst.market_engine.analyze(
                candles_by_timeframe
            )
        ),
        details=lambda value: (
            "Market state generated"
        ),
    )



    # ========================================================
    # STAGE 5
    # PATTERN ENGINE
    # ========================================================


    timeframe_intelligence = {

        int(CONFIG.BASE_TIMEFRAME_SECONDS):
            market.base_30s,

        int(CONFIG.TIMEFRAME_1M_SECONDS):
            market.setup_1m,

        int(CONFIG.TIMEFRAME_5M_SECONDS):
            market.context_5m,

    }



    patterns = execute_stage(
        results=results,
        name="Pattern Engine",
        operation=lambda: {

            timeframe: (
                analyst.pattern_engine.analyze(

                    candles=candles,

                    technical=(
                        timeframe_intelligence[
                            timeframe
                        ].technical
                    ),

                    structure=(
                        timeframe_intelligence[
                            timeframe
                        ].structure
                    ),

                )
            )

            for timeframe, candles
            in candles_by_timeframe.items()

        },
        details=lambda value: (
            f"Generated {len(value)} pattern snapshots"
        ),
    )



    # ========================================================
    # STAGE 6
    # REGIME DETECTION
    # ========================================================


    regime = execute_stage(
        results=results,
        name="Regime Detection",
        operation=lambda: (
            analyst.regime_detector.detect(

                market=market,

                patterns_by_timeframe=patterns,

            )
        ),
        details=lambda value: (
            f"Regime={getattr(value, 'primary_regime', 'UNKNOWN')}"
        ),
    )



    # ========================================================
    # STAGE 7
    # AGENT DEBATE
    # ========================================================


    debate = execute_stage(
        results=results,
        name="Agent Debate",
        operation=lambda: (

            analyst.coordinator.evaluate(

                market=market,

                regime=regime,

                patterns_by_timeframe=patterns,

                session_context={

                    "test_mode": True,

                    "data_stale": False,

                    "data_quality_score": 1.0,

                },

            )

        ),
        details=lambda value: (

            f"Consensus="
            f"{getattr(value, 'consensus_confidence', 0.0)}"

        ),
    )



    # ========================================================
    # STAGE 8
    # WORLD MODEL
    # ========================================================


    feature_vector = execute_stage(
        results=results,
        name="Memory Feature Vector",
        operation=lambda: {

            "market.multi_timeframe_bias":
                float(
                    market.multi_timeframe_bias
                ),

            "market.alignment_score":
                float(
                    market.alignment_score
                ),

            "market.conflict_score":
                float(
                    market.conflict_score
                ),

            "market.market_quality":
                float(
                    market.market_quality
                ),

            "regime.regime_confidence":
                float(
                    regime.regime_confidence
                ),

            "debate.consensus_confidence":
                float(
                    debate.consensus_confidence
                ),

        },
        details=lambda value: (
            f"{len(value)} features"
        ),
    )



    world = execute_stage(
        results=results,
        name="World Model",
        operation=lambda: (

            analyst.world_model.build(

                market=market,

                regime=regime,

                debate=debate,

                memory_feature_vector=feature_vector,

            )

        ),
        details=lambda _: (
            "World state created"
        ),
    )



    # ========================================================
    # STAGE 9
    # SCENARIO SIMULATION
    # ========================================================


    simulation = execute_stage(
        results=results,
        name="Scenario Simulation",
        operation=lambda: (

            analyst.scenario_engine.simulate(
                world
            )

        ),
        details=lambda _: (
            "Future scenarios generated"
        ),
    )



# ============================================================
# END PART 2/3
#
# Next:
# Decision Fusion
# Confidence
# Full Decision Runtime
# Final Report
#
# ============================================================
# ============================================================
# START PART 3/3
#
# Decision Fusion
# Confidence Calibration
# Full Decision Runtime
# Final Validation Report
#
# ============================================================



    # ========================================================
    # STAGE 10
    # KNOWLEDGE SUPPORT
    # ========================================================


    knowledge_support = execute_stage(
        results=results,
        name="Knowledge Support",
        operation=lambda: (

            analyst.knowledge.directional_support(

                regime=(
                    regime.primary_regime
                ),

                tags=(
                    build_pattern_tags(
                        patterns
                    )
                ),

            )

        ),
        details=lambda value: (
            f"Knowledge items="
            f"{value.get('count', 0)}"
        ),
    )



    # ========================================================
    # STAGE 11
    # DECISION FUSION
    # ========================================================


    memory_summary = execute_stage(
        results=results,
        name="Memory Similarity Search",
        operation=lambda: (

            analyst.memory.summarize_similar(

                world.similar_cases

            )

        ),
        details=lambda _: (
            "Historical similarity loaded"
        ),
    )



    fusion = execute_stage(
        results=results,
        name="Decision Fusion",
        operation=lambda: (

            analyst.decision_fusion.fuse(

                market=market,

                regime=regime,

                debate=debate,

                world=world,

                simulation=simulation,

                memory_summary=memory_summary,

                knowledge_support=knowledge_support,

            )

        ),
        details=lambda _: (
            "Decision signals combined"
        ),
    )



    # ========================================================
    # STAGE 12
    # CONFIDENCE CALIBRATION
    # ========================================================


    calibrated = execute_stage(
        results=results,
        name="Confidence Calibration",
        operation=lambda: (

            analyst.confidence_engine.calibrate(

                decision=fusion,

                regime=regime,

            )

        ),
        details=lambda value: (

            f"confidence="
            f"{getattr(value, 'calibrated_confidence', 0.0)}"

        ),
    )



    # ========================================================
    # STAGE 13
    # FULL DECISION RUNTIME
    # ========================================================


    runtime_result = execute_stage(
        results=results,
        name="Full Decision Runtime",
        operation=lambda: (

            analyst.full_decision_runtime.run(

                consensus_result=(

                    build_runtime_consensus(
                        debate
                    )

                ),


                calibrated_decision=calibrated,


                market_multiplier=(

                    calculate_market_multiplier(
                        market
                    )

                ),


                knowledge_reliability=(

                    calculate_knowledge_reliability(
                        knowledge_support
                    )

                ),


                calibration_factor=(

                    calculate_calibration_factor(
                        calibrated
                    )

                ),


                market_mode=(

                    detect_market_mode(

                        market=market,

                        regime=regime,

                    )

                ),


                data_health=(

                    calculate_data_health(
                        market
                    )

                ),


                microstructure_valid=(

                    validate_microstructure(
                        regime
                    )

                ),


                market=market,

                regime=regime,

                debate=debate,

                simulation=simulation,

            )

        ),
        details=lambda value: (

            f"stage="
            f"{getattr(value, 'stage', 'UNKNOWN')} | "

            f"allowed="
            f"{getattr(value, 'allowed', False)}"

        ),
    )



    # ========================================================
    # FINAL REPORT
    # ========================================================


    print()

    print(
        "=" * 72
    )

    print(
        "FINAL DECISION RUNTIME REPORT"
    )

    print(
        "=" * 72
    )



    for result in results:

        status = (
            "PASS"
            if result.passed
            else
            "FAIL"
        )


        print(

            f"[{status}] "

            f"{result.name} | "

            f"{result.duration_ms:.2f} ms | "

            f"{result.details}"

        )



    print()

    print(
        "=" * 72
    )

    print(
        "DECISION SUMMARY"
    )

    print(
        "=" * 72
    )


    print(

        {

            "stage":
                getattr(
                    runtime_result,
                    "stage",
                    None,
                ),


            "allowed":
                getattr(
                    runtime_result,
                    "allowed",
                    None,
                ),


            "confidence":
                getattr(
                    runtime_result,
                    "confidence",
                    None,
                ),


            "blockers":
                getattr(
                    runtime_result,
                    "blockers",
                    [],
                ),

        }

    )



    failed = [

        result.name

        for result in results

        if not result.passed

    ]



    if failed:

        raise RuntimeError(

            "Failed stages: "

            +

            ", ".join(
                failed
            )

        )



    print()

    print(
        "FULL END TO END DECISION TEST PASSED"
    )





# ============================================================
# SCRIPT ENTRY
# ============================================================


if __name__ == "__main__":

    run()



# ============================================================
# END PART 3/3
#
# FILE COMPLETE
#
# ============================================================