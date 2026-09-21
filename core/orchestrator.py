# ============================================================
# START PART 1/7
# core/orchestrator.py
# Imports + Runtime Contracts + Analyst Initialization
# ============================================================

import asyncio
import json
import logging
import time

from dataclasses import asdict, dataclass, is_dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Mapping, Optional

from agents.analyst_coordinator import AnalystCoordinator
from communication.voice_alert import VoiceAlert
from confidence.adaptive_confidence_controller import (
    AdaptiveConfidenceController,
)
from confidence.confidence_threshold_manager import (
    ConfidenceThresholdManager,
)
from config import CONFIG
from core.session_manager import SessionManager
from data.candle_builder import CandleBuilder
from data.data_manager import DataManager
from data.pocket_connector import (
    HistoricalCandle,
    MarketTick,
    PocketConnector,
)
from debug_tick_recorder import TickRecorder
from decision.confidence_engine import ConfidenceEngine
from decision.consensus_decision_gate import ConsensusDecisionGate
from decision.decision_fusion import DecisionFusionEngine
from decision.explanation_engine import ExplanationEngine
from intelligence.market_intelligence import MarketIntelligenceEngine
from intelligence.otc_behavior_engine import OTCBehaviorEngine
from intelligence.pattern_engine import PatternEngine, PatternSnapshot
from intelligence.regime_detector import RegimeDetector
from learning.continuous_learning import ContinuousLearningEngine
from learning.goal_manager import GoalManager
from memory.knowledge_base import KnowledgeBase
from memory.memory_manager import MemoryManager
from memory.trade_journal import TradeJournal
from pipeline.full_decision_runtime import FullDecisionRuntime
from risk.risk_manager import FinalRiskDecision, RiskManager
from simulation.scenario_engine import ScenarioEngine
from simulation.world_model import WorldModel
from ui.terminal_dashboard import TerminalDashboard


# ============================================================
# INTERNAL RUNTIME CONTRACTS
# ============================================================


@dataclass(slots=True)
class _PendingEvaluation:
    case_id: str
    journal_id: str
    action: str
    entry_timestamp: float
    due_timestamp: float
    entry_price: float
    atr: float


@dataclass(slots=True)
class _RuntimeConsensus:
    """
    Normalized consensus contract consumed by FullDecisionRuntime.
    """

    status: str
    confidence: float


# ============================================================
# MAIN ANALYST ORCHESTRATOR
# ============================================================


class Analyst:
    """
    Main runtime orchestrator for the Personal AI Trading Analyst.

    Pipeline:

        Data Feed
            |
        Candle Builder
            |
        Market Intelligence
            |
        Pattern + Regime Analysis
            |
        Multi-Agent Debate
            |
        World Model
            |
        Scenario Simulation
            |
        Decision Fusion
            |
        Confidence Calibration
            |
        Full Decision Runtime
            |
        Risk Firewall
            |
        Dashboard + Learning

    Architecture rules:

    - No execution.
    - No direct trading.
    - No hidden decisions.
    - Every decision passes through runtime control.
    """

    def __init__(self) -> None:
        # ====================================================
        # SAFETY
        # ====================================================

        if bool(CONFIG.EXECUTION_ENABLED):
            raise RuntimeError(
                "EXECUTION_ENABLED must remain False. "
                "This project is advisory only."
            )

        # ====================================================
        # DATA LAYER
        # ====================================================

        self.session = SessionManager()
        self.connector = PocketConnector()
        self.data = DataManager()
        self.candle_builder = CandleBuilder()

        # ====================================================
        # INTELLIGENCE LAYER
        # ====================================================

        self.market_engine = MarketIntelligenceEngine()
        self.pattern_engine = PatternEngine()
        self.otc_behavior_engine = OTCBehaviorEngine()
        self.regime_detector = RegimeDetector()
        self.coordinator = AnalystCoordinator()

        # ====================================================
        # MEMORY / KNOWLEDGE / LEARNING
        # ====================================================

        self.memory = MemoryManager()
        self.knowledge = KnowledgeBase()

        self.journal = TradeJournal(
            str(
                CONFIG.JOURNAL_DIR
                / "trades.jsonl"
            )
        )

        self.learning = ContinuousLearningEngine(
            memory=self.memory,
            knowledge=self.knowledge,
            journal=self.journal,
        )

        self.goals = GoalManager(
            memory=self.memory,
            knowledge=self.knowledge,
            journal=self.journal,
        )

        # ====================================================
        # DECISION INTELLIGENCE
        # ====================================================

        self.world_model = WorldModel(
            memory=self.memory
        )

        self.scenario_engine = ScenarioEngine()

        self.decision_fusion = DecisionFusionEngine()

        self.confidence_engine = ConfidenceEngine(
            memory=self.memory
        )

        # ====================================================
        # FINAL RISK FIREWALL
        # ====================================================

        # One shared RiskManager instance.
        # FullDecisionRuntime and the analyst reference the same object.
        self.risk_manager = RiskManager()

        # ====================================================
        # FULL DECISION RUNTIME
        # ====================================================

        self.full_decision_runtime = FullDecisionRuntime(
            adaptive_confidence=AdaptiveConfidenceController(),
            threshold_manager=ConfidenceThresholdManager(),
            decision_gate=ConsensusDecisionGate(),
            risk_manager=self.risk_manager,
        )

        # ====================================================
        # EXPLANATION LAYER
        # ====================================================

        self.explanation_engine = ExplanationEngine()
        self._last_explanation = None

        # ====================================================
        # UI / OBSERVABILITY
        # ====================================================

        self.dashboard = TerminalDashboard()

        self.logger = self._build_logger()

        self.tick_recorder = TickRecorder()

        self.voice_alert = VoiceAlert()

        # ====================================================
        # PENDING OUTCOME EVALUATIONS
        # ====================================================

        self._pending: list[_PendingEvaluation] = []

        self._last_recorded_market_timestamp: Optional[float] = None

        self._last_ui_refresh = 0.0

        # ====================================================
        # LEARNING STATE
        # ====================================================

        summary = self.memory.summary()

        self._last_learning_resolved = int(
            summary.resolved_cases
        )

        self._last_goal_review_resolved = int(
            summary.resolved_cases
        )

        # ====================================================
        # LAST RUNTIME SNAPSHOTS
        # ====================================================

        self._last_market = None
        self._last_regime = None
        self._last_debate = None
        self._last_world = None
        self._last_simulation = None

        self._last_final: Optional[
            FinalRiskDecision
        ] = None


# ============================================================
# END PART 1/7
# Next: Runtime lifecycle + stream handling + ingestion
# ============================================================
# ============================================================
# START PART 2/7
# Runtime Lifecycle + Stream Handling + Data Ingestion
# ============================================================


    def start(self) -> None:
        """
        Synchronous entry point used by main.py.
        """

        try:
            asyncio.run(
                self._run()
            )

        except KeyboardInterrupt:
            self.session.request_stop(
                "keyboard_interrupt"
            )


    async def _run(self) -> None:
        """
        Main analyst runtime lifecycle.

        Responsibilities:

        - Start session/dashboard.
        - Connect to market data provider.
        - Bootstrap historical candles.
        - Wait for live 5m confirmation.
        - Consume live ticks.
        - Trigger analysis on newly closed base candles.
        - Recover from stream termination.
        - Write final session report.
        """

        self.session.start()
        self.dashboard.start()

        fatal_error: Optional[str] = None
        stream = None

        try:
            # =================================================
            # CONNECT DATA PROVIDER
            # =================================================

            await self.connector.connect()

            # =================================================
            # HISTORICAL BOOTSTRAP
            # =================================================

            seeded = await self._bootstrap_history()

            # =================================================
            # CREATE LIVE STREAM
            # =================================================

            stream = self.connector.stream_ticks()

            # =================================================
            # LIVE CONFIRMATION WARMUP
            # =================================================

            if seeded:
                stream = await self._wait_for_5m_confirmation_candles(
                    stream
                )

                self.logger.info(
                    "STREAM AFTER WARMUP TYPE=%s",
                    type(stream),
                )

                await self._analyze_current(
                    record_advisory=False,
                    decision_timestamp=None,
                )

            # =================================================
            # MAIN TICK LOOP
            # =================================================

            pending_tick_task = None

            while not self.session.should_stop():
                try:
                    if pending_tick_task is None:
                        pending_tick_task = asyncio.create_task(
                            anext(stream)
                        )

                    tick = await asyncio.wait_for(
                        asyncio.shield(
                            pending_tick_task
                        ),
                        timeout=max(
                            float(
                                CONFIG.UI_REFRESH_SECONDS
                            ),
                            0.5,
                        ),
                    )

                    self.logger.info(
                        "LIVE TICK RECEIVED %s",
                        tick.timestamp,
                    )

                    pending_tick_task = None

                except asyncio.TimeoutError:
                    self._heartbeat()
                    continue

                except StopAsyncIteration:
                    # A provider stream may terminate during
                    # reconnects/lifecycle transitions.
                    #
                    # Recreate the consumer instead of killing
                    # the analyst runtime.

                    self.logger.warning(
                        "Tick stream ended. "
                        "Recreating consumer stream."
                    )

                    if pending_tick_task is not None:
                        pending_tick_task.cancel()

                        try:
                            await pending_tick_task
                        except BaseException:
                            pass

                        pending_tick_task = None

                    try:
                        await stream.aclose()
                    except Exception:
                        pass

                    await asyncio.sleep(
                        1.0
                    )

                    stream = (
                        self.connector.stream_ticks()
                    )

                    continue

                # =================================================
                # INGEST LIVE TICK
                # =================================================

                closed_by_timeframe = (
                    self._ingest_live_tick(
                        tick
                    )
                )

                # =================================================
                # ANALYZE ONLY ON CLOSED BASE CANDLE
                # =================================================

                if closed_by_timeframe.get(
                    CONFIG.BASE_TIMEFRAME_SECONDS,
                    [],
                ):
                    await self._analyze_current(
                        record_advisory=True,
                        decision_timestamp=tick.timestamp,
                    )

                else:
                    self._heartbeat()

        except Exception as exc:
            fatal_error = (
                f"{type(exc).__name__}: {exc}"
            )

            self.logger.exception(
                "Fatal analyst error: %s",
                exc,
            )

            self.session.request_stop(
                "fatal_error"
            )

        finally:
            # =================================================
            # STREAM CLEANUP
            # =================================================

            if stream is not None:
                try:
                    await stream.aclose()
                except Exception:
                    pass

            # =================================================
            # CONNECTOR CLEANUP
            # =================================================

            await self.connector.close()

            # =================================================
            # SESSION REPORT
            # =================================================

            self._write_session_report(
                fatal_error=fatal_error
            )


    async def _wait_for_5m_confirmation_candles(
        self,
        stream: Any,
    ) -> Any:
        """
        Wait for two new live closed 5-minute candles.

        Historical data provides context, but two new live 5m
        confirmations ensure that the runtime is synchronized
        with the current stream before normal analysis begins.
        """

        initial_5m_count = len(
            self._candles(
                CONFIG.TIMEFRAME_5M_SECONDS
            )
        )

        target = (
            initial_5m_count
            + 2
        )

        self.logger.info(
            "Waiting for two live closed 5m confirmation candles: "
            "current=%s target=%s",
            initial_5m_count,
            target,
        )

        while (
            len(
                self._candles(
                    CONFIG.TIMEFRAME_5M_SECONDS
                )
            )
            < target
        ):
            try:
                tick = await anext(
                    stream
                )

            except StopAsyncIteration:
                # Warmup stream failure must not kill
                # the complete analyst lifecycle.

                self.logger.warning(
                    "Warmup stream ended. "
                    "Recreating consumer stream."
                )

                try:
                    await stream.aclose()
                except Exception:
                    pass

                await asyncio.sleep(
                    max(
                        0.25,
                        float(
                            CONFIG.STREAM_RECONNECT_DELAY_SECONDS
                        ),
                    )
                )

                stream = (
                    self.connector.stream_ticks()
                )

                continue

            self._ingest_live_tick(
                tick
            )

            self._heartbeat()

        self.logger.info(
            "Two live 5m confirmation candles received. "
            "Analysis unlocked."
        )

        return stream


    def _ingest_live_tick(
        self,
        tick: MarketTick,
    ) -> dict[
        int,
        list[HistoricalCandle],
    ]:
        """
        Push one live tick through the runtime data pipeline.

        Warmup and the normal live loop use exactly the same
        ingestion path so runtime state cannot drift.
        """

        # =====================================================
        # RAW TICK DEBUG CAPTURE
        # =====================================================

        if (
            hasattr(
                self,
                "tick_recorder",
            )
            and self.tick_recorder
        ):
            try:
                self.tick_recorder.record(
                    tick
                )

            except Exception as exc:
                self.logger.warning(
                    "Tick recorder failed: %s",
                    exc,
                )

        # =====================================================
        # STORE RAW TICK
        # =====================================================

        self.data.add_tick(
            tick
        )

        # =====================================================
        # RESOLVE PENDING ANALYTICAL OUTCOMES
        # =====================================================

        self._resolve_pending(
            tick
        )

        # =====================================================
        # BUILD CANDLES
        # =====================================================

        closed_by_timeframe = (
            self.candle_builder.add_tick(
                tick
            )
        )

        # =====================================================
        # OBSERVABILITY
        # =====================================================

        if any(
            closed_by_timeframe.values()
        ):
            self.logger.info(
                "CANDLE CLOSED %s",
                {
                    timeframe: len(candles)
                    for timeframe, candles
                    in closed_by_timeframe.items()
                },
            )

        # =====================================================
        # STORE CLOSED CANDLES
        # =====================================================

        for candles in (
            closed_by_timeframe.values()
        ):
            self.data.add_candles(
                candles
            )

        return closed_by_timeframe


    async def _bootstrap_history(
        self,
    ) -> int:
        """
        Hybrid historical bootstrap.

        Strategy:

        1. Request enough closed 30s candles.
        2. Gracefully fallback to smaller requests.
        3. Build 1m and 5m context from available history.
        4. Keep the system in warmup until enough live context
           has been confirmed.
        """

        bootstrap_sizes = (
            240,
            220,
            200,
            120,
        )

        history: list[
            HistoricalCandle
        ] = []

        # =====================================================
        # FETCH HISTORY WITH FALLBACK SIZES
        # =====================================================

        for requested_count in (
            bootstrap_sizes
        ):
            try:
                self.logger.info(
                    "Requesting historical candles: %s",
                    requested_count,
                )

                history = await (
                    self.connector
                    .fetch_historical_candles(
                        timeframe_seconds=(
                            CONFIG.BASE_TIMEFRAME_SECONDS
                        ),
                        count=requested_count,
                    )
                )

                if history:
                    self.logger.info(
                        "Bootstrap received %s candles",
                        len(history),
                    )

                    break

            except Exception as exc:
                self.logger.warning(
                    "Historical request %s failed: %s",
                    requested_count,
                    exc,
                )

        # =====================================================
        # NO HISTORY AVAILABLE
        # =====================================================

        if not history:
            self.dashboard.show_warning(
                "Historical bootstrap unavailable. "
                "Waiting for live candles."
            )

            return 0

        # =====================================================
        # NORMALIZE HISTORY
        # =====================================================

        history = (
            self._deduplicate_candles(
                history
            )
        )

        history = await (
            self._closed_history_only(
                history
            )
        )

        if not history:
            self.dashboard.show_warning(
                "No closed historical candles available."
            )

            return 0

        # =====================================================
        # SEED CANDLE BUILDER
        # =====================================================

        emitted = (
            self.candle_builder
            .seed_base_candles(
                history
            )
        )

        # =====================================================
        # STORE GENERATED TIMEFRAMES
        # =====================================================

        stored = 0

        for candles in emitted.values():
            self.data.add_candles(
                candles
            )

            stored += len(
                candles
            )

        # =====================================================
        # CURRENT TIMEFRAME COUNTS
        # =====================================================

        counts = {
            timeframe: len(
                self._candles(
                    timeframe
                )
            )
            for timeframe
            in self.candle_builder.timeframes
        }

        self.logger.info(
            "Hybrid bootstrap complete: "
            "base=%s stored=%s counts=%s",
            len(history),
            stored,
            counts,
        )

        # =====================================================
        # INITIAL DASHBOARD STATE
        # =====================================================

        self.dashboard.update(
            session=(
                self.session.snapshot()
            ),
            connector=(
                self._connector_status()
            ),
            memory_summary=(
                self.memory.summary()
            ),
            learning_context=(
                self.learning.runtime_context()
            ),
            goal_context=(
                self.goals.runtime_context()
            ),
            status_message=(
                "Bootstrap loaded | "
                f"30s={counts.get(CONFIG.BASE_TIMEFRAME_SECONDS, 0)} "
                f"1m={counts.get(CONFIG.TIMEFRAME_1M_SECONDS, 0)} "
                f"5m={counts.get(CONFIG.TIMEFRAME_5M_SECONDS, 0)}"
            ),
        )

        return len(
            history
        )


    async def _closed_history_only(
        self,
        candles: list[
            HistoricalCandle
        ],
    ) -> list[
        HistoricalCandle
    ]:
        """
        Remove any historical candle that may still be forming.
        """

        if not candles:
            return []

        # =====================================================
        # RESOLVE PROVIDER TIME
        # =====================================================

        server_now = await (
            self.connector.server_time()
        )

        if server_now is None:
            now = time.time()

        else:
            now = (
                self._normalize_timestamp(
                    float(
                        server_now
                    )
                )
            )

        timeframe = float(
            CONFIG.BASE_TIMEFRAME_SECONDS
        )

        # =====================================================
        # KEEP CLOSED CANDLES ONLY
        # =====================================================

        closed = [
            candle
            for candle in candles
            if (
                candle.timestamp
                + timeframe
                <= now + 1.0
            )
        ]

        # Some unofficial endpoints do not expose a reliable
        # server clock. In that situation keeping everything
        # except the latest row is safer than accepting a
        # potentially forming candle as closed.

        if (
            not closed
            and len(candles) > 1
        ):
            return candles[:-1]

        return closed


# ============================================================
# END PART 2/7
# Next: Full Market Analysis + Decision Runtime Pipeline
# ============================================================
# ============================================================
# START PART 3/7
# Full Market Analysis + Decision Pipeline
# ============================================================


    async def _analyze_current(
        self,
        *,
        record_advisory: bool,
        decision_timestamp: Optional[float],
    ) -> Optional[FinalRiskDecision]:

        # =====================================================
        # LOAD AVAILABLE CANDLES
        # =====================================================

        candles_by_timeframe = {
            CONFIG.BASE_TIMEFRAME_SECONDS:
                self._candles(
                    CONFIG.BASE_TIMEFRAME_SECONDS
                ),

            CONFIG.TIMEFRAME_1M_SECONDS:
                self._candles(
                    CONFIG.TIMEFRAME_1M_SECONDS
                ),

            CONFIG.TIMEFRAME_5M_SECONDS:
                self._candles(
                    CONFIG.TIMEFRAME_5M_SECONDS
                ),
        }


        # =====================================================
        # OTC BEHAVIOR OBSERVATION
        #
        # Telemetry only.
        # Does not modify decision directly.
        # =====================================================

        try:

            recent_prices = []

            try:

                recent_ticks = list(
                    self.data.latest_ticks()
                )[-120:]


                recent_prices = [
                    float(tick.price)
                    for tick in recent_ticks
                ]


            except Exception:

                recent_prices = []


            # Fallback to candle closes
            if len(recent_prices) < 10:

                recent_prices = [
                    float(candle.close)

                    for candle in
                    candles_by_timeframe[
                        CONFIG.BASE_TIMEFRAME_SECONDS
                    ][-120:]
                ]


            otc_profile = (
                self.otc_behavior_engine.analyze(
                    recent_prices
                )
            )


            self.logger.info(
                "OTC PROFILE GENERATED: %s",
                otc_profile.as_dict(),
            )


        except Exception as exc:

            self.logger.warning(
                "OTC PROFILE FAILED: %s",
                exc,
            )



        # =====================================================
        # DATA AVAILABILITY CHECK
        # =====================================================

        if any(
            not candles

            for candles
            in candles_by_timeframe.values()
        ):

            self._render_latest(
                status_message=(
                    "Waiting for all 30s / 1m / 5m "
                    "closed candle streams..."
                )
            )

            return None



        # =====================================================
        # MARKET INTELLIGENCE
        # =====================================================

        market = (
            self.market_engine.analyze(
                candles_by_timeframe
            )
        )


        timeframe_intelligence = {

            CONFIG.BASE_TIMEFRAME_SECONDS:
                market.base_30s,

            CONFIG.TIMEFRAME_1M_SECONDS:
                market.setup_1m,

            CONFIG.TIMEFRAME_5M_SECONDS:
                market.context_5m,

        }



        # =====================================================
        # PATTERN ANALYSIS
        # =====================================================

        patterns: dict[
            int,
            PatternSnapshot,
        ] = {}


        for timeframe, candles in (
            candles_by_timeframe.items()
        ):

            intel = (
                timeframe_intelligence[
                    timeframe
                ]
            )


            patterns[timeframe] = (
                self.pattern_engine.analyze(
                    candles=candles,
                    technical=intel.technical,
                    structure=intel.structure,
                )
            )



        # =====================================================
        # REGIME DETECTION
        # =====================================================

        regime = (
            self.regime_detector.detect(
                market=market,
                patterns_by_timeframe=patterns,
            )
        )



        # =====================================================
        # AGENT DEBATE
        # =====================================================

        runtime_context = (
            self._runtime_context()
        )


        debate = (
            self.coordinator.evaluate(
                market=market,
                regime=regime,
                patterns_by_timeframe=patterns,
                session_context=runtime_context,
            )
        )



        # =====================================================
        # MEMORY FEATURE VECTOR
        # =====================================================

        feature_vector = (
            self._memory_feature_vector(
                market=market,
                regime=regime,
                debate=debate,
            )
        )



        # =====================================================
        # WORLD MODEL
        # =====================================================

        world = (
            self.world_model.build(
                market=market,
                regime=regime,
                debate=debate,
                memory_feature_vector=feature_vector,
            )
        )



        # =====================================================
        # SCENARIO SIMULATION
        # =====================================================

        simulation = (
            self.scenario_engine.simulate(
                world
            )
        )



        # =====================================================
        # MEMORY SIMILAR CASES
        # =====================================================

        memory_summary_for_fusion = (
            self.memory.summarize_similar(
                world.similar_cases
            )
        )



        # =====================================================
        # KNOWLEDGE SUPPORT
        # =====================================================

        tags = (
            self._pattern_tags(
                patterns
            )
        )


        knowledge_support = (
            self.knowledge.directional_support(
                regime=(
                    regime.primary_regime
                ),
                tags=tags,
            )
        )


        if int(
            knowledge_support.get(
                "count",
                0,
            )
            or 0
        ) == 0:

            knowledge_support = (
                self.knowledge.directional_support(
                    regime=(
                        regime.primary_regime
                    ),
                )
            )



        # =====================================================
        # DECISION FUSION
        # =====================================================

        fusion = (
            self.decision_fusion.fuse(
                market=market,
                regime=regime,
                debate=debate,
                world=world,
                simulation=simulation,
                memory_summary=(
                    memory_summary_for_fusion
                ),
                knowledge_support=(
                    knowledge_support
                ),
            )
        )



        # =====================================================
        # CONFIDENCE CALIBRATION
        # =====================================================

        calibrated = (
            self.confidence_engine.calibrate(
                decision=fusion,
                regime=regime,
            )
        )



        # =====================================================
        # FULL DECISION RUNTIME
        # =====================================================

        runtime_result = (
            self.full_decision_runtime.run(
                consensus_result=(
                    self._build_runtime_consensus(
                        debate
                    )
                ),

                calibrated_decision=calibrated,

                market_multiplier=(
                    self._calculate_market_multiplier(
                        market
                    )
                ),

                knowledge_reliability=(
                    self._calculate_knowledge_reliability(
                        knowledge_support
                    )
                ),

                calibration_factor=(
                    self._calculate_calibration_factor(
                        calibrated
                    )
                ),

                market_mode=(
                    self._detect_market_mode(
                        market=market,
                        regime=regime,
                        runtime_context=runtime_context,
                    )
                ),

                data_health=(
                    self._calculate_data_health(
                        market=market,
                        runtime_context=runtime_context,
                    )
                ),

                microstructure_valid=(
                    self._validate_microstructure(
                        market=market,
                        regime=regime,
                        runtime_context=runtime_context,
                    )
                ),

                market=market,

                regime=regime,

                debate=debate,

                simulation=simulation,

            )
        )



        # =====================================================
        # CONVERT RUNTIME RESULT
        # TO FINAL RISK DECISION CONTRACT
        # =====================================================

        final = (
            self._resolve_runtime_final_decision(
                runtime_result=runtime_result,
                calibrated=calibrated,
                market=market,
                regime=regime,
                debate=debate,
                simulation=simulation,
                runtime_context=runtime_context,
            )
        )



        # =====================================================
        # DECISION TRACE
        # =====================================================

        self._write_decision_trace(
            market=market,
            regime=regime,
            debate=debate,
            world=world,
            simulation=simulation,
            fusion=fusion,
            calibrated=calibrated,
            runtime_result=runtime_result,
            final=final,
        )


# ============================================================
# END PART 3/7
# Next: Explanation + Dashboard + Advisory Recording
# ============================================================
# ============================================================
# START PART 4/7
# Explanation + Dashboard + Advisory Recording
# ============================================================


        # =====================================================
        # EXPLANATION ENGINE
        # =====================================================

        self._last_explanation = (
            self.explanation_engine.explain(
                fusion_decision=fusion,
                calibrated_decision=calibrated,
                risk_result=final,
            )
        )


        self.logger.info(
            "EXPLANATION GENERATED: %s",
            self._last_explanation.as_dict(),
        )



        # =====================================================
        # STORE LAST RUNTIME SNAPSHOTS
        # =====================================================

        self._last_market = market

        self._last_regime = regime

        self._last_debate = debate

        self._last_world = world

        self._last_simulation = simulation

        self._last_final = final



        # =====================================================
        # VOICE ALERT
        # =====================================================

        self.voice_alert.check(
            final.advisory_action
        )



        # =====================================================
        # DASHBOARD UPDATE
        # =====================================================

        self.dashboard.update(
            session=(
                self.session.snapshot()
            ),

            connector=(
                self._connector_status()
            ),

            market=market,

            regime=regime,

            debate=debate,

            world=world,

            simulation=simulation,

            final_decision=final,

            memory_summary=(
                self.memory.summary()
            ),

            learning_context=(
                self.learning.runtime_context()
            ),

            goal_context=(
                self.goals.runtime_context()
            ),

            status_message=(
                self._analysis_status(
                    final
                )
            ),
        )



        # =====================================================
        # STORE ADVISORY RESULT
        # =====================================================

        if record_advisory:

            self._record_advisory(
                decision_timestamp=(
                    float(decision_timestamp)
                    if decision_timestamp is not None
                    else time.time()
                ),

                market=market,

                regime=regime,

                debate=debate,

                patterns=patterns,

                final=final,

                feature_vector=feature_vector,
            )



        return final





    # ========================================================
    # DECISION TRACE
    # ========================================================


    def _write_decision_trace(
        self,
        *,
        market: Any,
        regime: Any,
        debate: Any,
        world: Any,
        simulation: Any,
        fusion: Any,
        calibrated: Any,
        runtime_result: Any,
        final: FinalRiskDecision,
    ) -> None:

        """
        Writes decision visibility information.

        Trace is observability only.
        It never changes decision logic.
        """

        try:

            trace = {

                "analysis_start": True,

                "market_state": "OK",

                "regime": getattr(
                    regime,
                    "primary_regime",
                    None,
                ),

                "agents": "OK",

                "world_model": "OK",

                "simulation": "OK",

                "fusion": "OK",


                "calibrated_confidence": getattr(
                    calibrated,
                    "calibrated_confidence",
                    None,
                ),


                "runtime_stage": getattr(
                    runtime_result,
                    "stage",
                    None,
                ),


                "runtime_blockers": list(
                    getattr(
                        runtime_result,
                        "blockers",
                        [],
                    )
                    or []
                ),


                "risk_review": "OK",


                "final_decision": getattr(
                    final,
                    "advisory_action",
                    None,
                ),


                "blocked": getattr(
                    final,
                    "blocked",
                    None,
                ),


                "block_reasons": list(
                    getattr(
                        final,
                        "block_reasons",
                        [],
                    )
                    or []
                ),

            }


            self.logger.info(
                "DECISION TRACE %s",
                json.dumps(
                    trace,
                    ensure_ascii=False,
                ),
            )


        except Exception as exc:

            # Trace must never affect analyst pipeline.

            self.logger.warning(
                "Decision trace failed: %s",
                exc,
            )





    # ========================================================
    # ADVISORY MEMORY RECORDING
    # ========================================================


    def _record_advisory(
        self,
        *,
        decision_timestamp: float,
        market: Any,
        regime: Any,
        debate: Any,
        patterns: Mapping[
            int,
            PatternSnapshot,
        ],
        final: FinalRiskDecision,
        feature_vector: Mapping[
            str,
            float,
        ],
    ) -> None:


        # =====================================================
        # PREVENT DUPLICATE RECORDING
        # =====================================================

        if (

            self._last_recorded_market_timestamp
            is not None

            and market.timestamp
            <= self._last_recorded_market_timestamp

        ):

            return



        self._last_recorded_market_timestamp = float(
            market.timestamp
        )



        # =====================================================
        # TAG EXTRACTION
        # =====================================================

        tags = (
            self._pattern_tags(
                patterns
            )
        )



        # =====================================================
        # MEMORY CASE
        # =====================================================

        case = self.memory.add_case(

            asset=market.asset,

            timeframe_seconds=(
                CONFIG.BASE_TIMEFRAME_SECONDS
            ),

            timestamp=float(
                decision_timestamp
            ),

            price=float(
                market.price
            ),

            regime=(
                regime.primary_regime
            ),

            market_state=(
                market.context_state
            ),

            direction=(
                final.direction
            ),

            feature_vector=feature_vector,

            tags=tags,

            confidence=(
                final.calibrated_confidence
            ),

            uncertainty=(
                final.uncertainty
            ),

            notes=(
                tuple(
                    final.reasons[:8]
                )
            ),
        )



        # =====================================================
        # JOURNAL ENTRY
        # =====================================================

        expiry_seconds = int(
            CONFIG.BASE_TIMEFRAME_SECONDS
        )



        journal_entry = self.journal.create(

            asset=market.asset,

            direction=(
                final.advisory_action
            ),

            confidence=(
                final.calibrated_confidence
            ),

            price=market.price,

            expiry_seconds=expiry_seconds,


            analysis={

                "execution": False,

                "kind": (
                    "advisory_evaluation"
                ),

                "market_timestamp": (
                    market.timestamp
                ),

                "regime": (
                    regime.primary_regime
                ),

                "risk_score": (
                    final.risk_score
                ),

                "uncertainty": (
                    final.uncertainty
                ),

                "signal_strength": (
                    final.signal_strength
                ),

                "blocked": (
                    final.blocked
                ),

                "agent_consensus": (
                    debate.consensus_direction
                ),

                "tags": list(tags),

            },
        )



        # =====================================================
        # PENDING OUTCOME
        # =====================================================

        atr = max(
            float(
                market.base_30s
                .technical
                .atr
            ),

            0.0,
        )



        self._pending.append(

            _PendingEvaluation(

                case_id=case.case_id,

                journal_id=journal_entry.id,

                action=(
                    final.advisory_action
                ),

                entry_timestamp=(
                    float(
                        decision_timestamp
                    )
                ),

                due_timestamp=(

                    float(
                        decision_timestamp
                    )
                    + expiry_seconds

                ),

                entry_price=(
                    float(
                        market.price
                    )
                ),

                atr=atr,

            )

        )


# ============================================================
# END PART 4/7
# Next: Outcome Resolution + Learning Loop
# ============================================================

# ============================================================
# START PART 5/7
# Outcome Resolution + Learning Loop
# ============================================================



    def _resolve_pending(
        self,
        tick: MarketTick,
    ) -> None:


        if not self._pending:
            return



        remaining: list[
            _PendingEvaluation
        ] = []


        resolved_now = 0



        for pending in self._pending:


            # =================================================
            # WAIT UNTIL EXPIRY TIME
            # =================================================

            if (
                tick.timestamp
                <
                pending.due_timestamp
            ):

                remaining.append(
                    pending
                )

                continue



            # =================================================
            # SCORE ANALYTICAL OUTCOME
            # =================================================

            result, score = (
                self._score_outcome(
                    pending=pending,
                    exit_price=tick.price,
                )
            )



            # =================================================
            # UPDATE MEMORY
            # =================================================

            try:

                self.memory.update_outcome(

                    pending.case_id,

                    outcome=result,

                    outcome_score=score,

                    outcome_timestamp=(
                        tick.timestamp
                    ),

                    note=(

                        f"analytical expiry "
                        f"evaluation at "
                        f"{tick.price:.8f}; "

                        "no real order was executed"

                    ),

                )


            except Exception as exc:

                self.logger.warning(
                    "Memory outcome update failed "
                    "for %s: %s",
                    pending.case_id,
                    exc,
                )



            # =================================================
            # UPDATE JOURNAL
            # =================================================

            try:

                self.journal.close(

                    pending.journal_id,

                    result=result,

                    pnl=score,

                )


            except Exception as exc:

                self.logger.warning(
                    "Journal outcome update failed "
                    "for %s: %s",
                    pending.journal_id,
                    exc,
                )



            resolved_now += 1



        self._pending = remaining



        # =====================================================
        # TRIGGER LEARNING
        # =====================================================

        if resolved_now:

            self._refresh_learning_if_due()





    def _score_outcome(
        self,
        *,
        pending: _PendingEvaluation,
        exit_price: float,
    ) -> tuple[
        str,
        float,
    ]:


        move = (
            float(exit_price)
            -
            pending.entry_price
        )



        # =====================================================
        # BUY RESULT
        # =====================================================

        if pending.action == "BUY":

            if move > 0:
                return (
                    "CORRECT",
                    1.0,
                )

            if move < 0:
                return (
                    "WRONG",
                    -1.0,
                )

            return (
                "NEUTRAL",
                0.0,
            )



        # =====================================================
        # SELL RESULT
        # =====================================================

        if pending.action == "SELL":

            if move < 0:
                return (
                    "CORRECT",
                    1.0,
                )

            if move > 0:
                return (
                    "WRONG",
                    -1.0,
                )

            return (
                "NEUTRAL",
                0.0,
            )



        # =====================================================
        # WAIT QUALITY
        # =====================================================

        quiet_threshold = max(

            pending.atr * 0.35,

            pending.entry_price * 1e-6,

        )



        if abs(move) <= quiet_threshold:

            return (
                "CORRECT_WAIT",
                1.0,
            )



        return (
            "MISSED_MOVE",
            -1.0,
        )







    def _refresh_learning_if_due(
        self,
        *,
        force_if_empty: bool = False,
    ) -> None:


        summary = (
            self.memory.summary()
        )


        resolved = int(
            summary.resolved_cases
        )



        # =====================================================
        # CONTINUOUS LEARNING CHECK
        # =====================================================

        learning_interval = max(

            int(
                CONFIG.LEARNING_MIN_NEW_CASES
            ),

            1,

        )



        knowledge_empty = (

            self.knowledge.summary()
            .get(
                "total_items",
                0,
            )
            == 0

        )



        should_learn = (

            resolved
            -
            self._last_learning_resolved

            >=

            learning_interval

        )



        if (

            force_if_empty

            and knowledge_empty

            and resolved >= learning_interval

        ):

            should_learn = True




        if should_learn:


            try:

                report = (
                    self.learning.learn(
                        asset=CONFIG.PAIR
                    )
                )


                self.logger.info(

                    "Learning pass: %s",

                    report.as_dict(),

                )


                self._last_learning_resolved = (
                    resolved
                )


            except Exception as exc:


                self.logger.exception(

                    "Continuous learning pass failed: %s",

                    exc,

                )



        # =====================================================
        # GOAL REVIEW CHECK
        # =====================================================


        goal_interval = max(

            int(
                CONFIG.GOAL_REVIEW_INTERVAL_CASES
            ),

            1,

        )



        should_review_goals = (

            resolved

            -

            self._last_goal_review_resolved

            >=

            goal_interval

        )



        if (

            force_if_empty

            and not self.goals.active_goals()

            and resolved >= goal_interval

        ):

            should_review_goals = True




        if should_review_goals:


            try:

                self.goals.review(

                    asset=CONFIG.PAIR

                )


                self._last_goal_review_resolved = (
                    resolved
                )


            except Exception as exc:


                self.logger.exception(

                    "Goal review failed: %s",

                    exc,

                )



# ============================================================
# END PART 5/7
# Next: Helper Methods + Runtime Intelligence Utilities
# ============================================================
# ============================================================
# START PART 6/7
# Runtime Intelligence Helpers + Consensus + Validation
# ============================================================


    def _build_runtime_consensus(
        self,
        debate: Any,
    ) -> _RuntimeConsensus:
        """
        Converts agent debate output
        into runtime consensus contract.
        """

        confidence = float(
            getattr(
                debate,
                "consensus_confidence",
                0.0,
            )
            or 0.0
        )


        disagreement = float(
            getattr(
                debate,
                "disagreement_score",
                0.0,
            )
            or 0.0
        )


        uncertainty = float(
            getattr(
                debate,
                "uncertainty_score",
                0.0,
            )
            or 0.0
        )


        reliable = (
            confidence >= 0.70
            and disagreement <= 0.35
            and uncertainty <= 0.40
        )


        return _RuntimeConsensus(
            status=(
                "RELIABLE_CONSENSUS"
                if reliable
                else "WEAK_CONSENSUS"
            ),
            confidence=confidence,
        )





    def _calculate_market_multiplier(
        self,
        market: Any,
    ) -> float:
        """
        Calculates market quality modifier.
        """

        quality = float(
            getattr(
                market,
                "market_quality",
                0.5,
            )
            or 0.5
        )


        return max(
            min(
                quality,
                1.0,
            ),
            0.0,
        )





    def _calculate_knowledge_reliability(
        self,
        knowledge_support: Mapping[str, Any],
    ) -> float:
        """
        Converts knowledge statistics
        into reliability score.
        """

        count = int(
            knowledge_support.get(
                "count",
                0,
            )
            or 0
        )


        success = float(
            knowledge_support.get(
                "success_rate",
                0.70,
            )
            or 0.70
        )


        sample_factor = min(
            count / 20,
            1.0,
        )


        reliability = (
            0.55
            +
            success * 0.30
            +
            sample_factor * 0.15
        )


        return max(
            min(
                reliability,
                1.0,
            ),
            0.55,
        )





    def _calculate_calibration_factor(
        self,
        calibrated: Any,
    ) -> float:
        """
        Calculates confidence calibration modifier.
        """

        confidence = float(
            getattr(
                calibrated,
                "calibrated_confidence",
                0.0,
            )
            or 0.0
        )


        if confidence <= 0:
            return 1.0


        return max(
            min(
                confidence / 0.85,
                1.05,
            ),
            0.75,
        )





    def _detect_market_mode(
        self,
        *,
        market: Any,
        regime: Any,
        runtime_context: Mapping[str, Any],
    ) -> str:
        """
        Dynamic threshold mode.
        """

        noise = float(
            getattr(
                regime,
                "noise_strength",
                0.0,
            )
            or 0.0
        )


        quality = float(
            getattr(
                market,
                "market_quality",
                0.5,
            )
            or 0.5
        )


        stale = bool(
            runtime_context.get(
                "data_stale",
                False,
            )
        )


        if (
            stale
            or noise >= 0.70
            or quality < 0.50
        ):
            return "DEFENSIVE"


        if (
            noise >= 0.45
            or quality < 0.70
        ):
            return "CAUTIOUS"


        return "NORMAL"





    def _calculate_data_health(
        self,
        *,
        market: Any,
        runtime_context: Mapping[str, Any],
    ) -> float:
        """
        Calculates input data quality score.
        """

        market_quality = float(
            getattr(
                market,
                "market_quality",
                0.5,
            )
            or 0.5
        )


        data_quality = float(
            runtime_context.get(
                "data_quality_score",
                0.5,
            )
            or 0.5
        )


        return max(
            min(
                (
                    market_quality
                    +
                    data_quality
                )
                / 2,
                1.0,
            ),
            0.0,
        )





    def _validate_microstructure(
        self,
        *,
        market: Any,
        regime: Any,
        runtime_context: Mapping[str, Any],
    ) -> bool:
        """
        Validates short-term market conditions.
        """

        if runtime_context.get(
            "data_stale",
            False,
        ):
            return False


        noise = float(
            getattr(
                regime,
                "noise_strength",
                0.0,
            )
            or 0.0
        )


        return noise < 0.80



# ============================================================
# END PART 6/7
# Next: Final Decision Resolver + Remaining Utilities
# ============================================================
# ============================================================
# START PART 7/7
# Final Decision Resolver + Remaining Utilities + Logger
# ============================================================


    def _resolve_runtime_final_decision(
        self,
        *,
        runtime_result: Any,
        calibrated: Any,
        market: Any,
        regime: Any,
        debate: Any,
        simulation: Any,
        runtime_context: Mapping[str, Any],
    ) -> FinalRiskDecision:
        """
        Converts runtime result into final
        compatible RiskDecision object.
        """


        evidence = getattr(
            runtime_result,
            "evidence",
            {},
        )


        if not isinstance(
            evidence,
            dict,
        ):
            evidence = {}



        risk_result = evidence.get(
            "risk"
        )



        if (
            risk_result
            and hasattr(
                risk_result,
                "blocked",
            )
        ):
            return risk_result



        return FinalRiskDecision(

            timestamp=time.time(),

            asset=getattr(
                market,
                "asset",
                CONFIG.PAIR,
            ),

            price=float(
                getattr(
                    market,
                    "price",
                    0.0,
                )
                or 0.0
            ),


            advisory_action="WAIT",

            direction="WAIT",


            calibrated_confidence=float(
                getattr(
                    calibrated,
                    "calibrated_confidence",
                    0.0,
                )
                or 0.0
            ),


            required_confidence=0.70,


            risk_score=1.0,

            uncertainty=1.0,

            data_risk=1.0,

            market_risk=1.0,

            model_risk=1.0,

            behavioral_risk=1.0,


            signal_strength="BLOCKED",


            blocked=True,


            block_reasons=(
                "RUNTIME_BLOCK",
            ),


            reasons=(

                str(
                    getattr(
                        runtime_result,
                        "stage",
                        "UNKNOWN",
                    )
                ),

            ),


            evidence={

                "runtime_stage": getattr(
                    runtime_result,
                    "stage",
                    "UNKNOWN",
                ),

                "runtime_blockers": list(
                    getattr(
                        runtime_result,
                        "blockers",
                        [],
                    )
                    or []
                ),

            },

        )





    def _candles(
        self,
        timeframe: int,
    ) -> list[HistoricalCandle]:

        candles = [

            candle

            for candle

            in self.data.latest_candles()

            if candle.timeframe_seconds
            == timeframe

        ]


        candles.sort(
            key=lambda candle:
            candle.timestamp
        )



        unique = {

            float(candle.timestamp):
            candle

            for candle in candles

        }


        return [

            unique[timestamp]

            for timestamp

            in sorted(unique)

        ]





    @staticmethod
    def _deduplicate_candles(
        candles: list[HistoricalCandle],
    ) -> list[HistoricalCandle]:


        unique = {}


        for candle in candles:

            unique[
                float(
                    candle.timestamp
                )
            ] = candle



        return [

            unique[timestamp]

            for timestamp

            in sorted(unique)

        ]





    @staticmethod
    def _memory_feature_vector(
        *,
        market: Any,
        regime: Any,
        debate: Any,
    ) -> dict[str, float]:

        return {


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


            "market.directional_conviction":
                float(
                    market.directional_conviction
                ),


            "market.compression_pressure":
                float(
                    market.compression_pressure
                ),


            "market.expansion_potential":
                float(
                    market.expansion_potential
                ),


            "market.rejection_pressure":
                float(
                    market.rejection_pressure
                ),


            "market.noise_score":
                float(
                    market.noise_score
                ),


            "market.market_quality":
                float(
                    market.market_quality
                ),


            "regime.directional_bias":
                float(
                    regime.directional_bias
                ),


            "regime.regime_confidence":
                float(
                    regime.regime_confidence
                ),


            "regime.trend_strength":
                float(
                    regime.trend_strength
                ),


            "debate.weighted_score":
                float(
                    debate.weighted_score
                ),


            "debate.consensus_confidence":
                float(
                    debate.consensus_confidence
                ),


            "debate.disagreement_score":
                float(
                    debate.disagreement_score
                ),


            "debate.uncertainty_score":
                float(
                    debate.uncertainty_score
                ),

        }





    def _runtime_context(self) -> dict[str, Any]:

        now = time.time()

        last_message = (
            self.connector.last_message_at
        )


        if last_message is None:

            seconds_since_last_tick = 0.0

            data_stale = False

            freshness = 0.50


        else:

            seconds_since_last_tick = max(

                now - last_message,

                0.0,

            )


            data_stale = (

                seconds_since_last_tick

                >

                float(
                    CONFIG.DATA_STALE_AFTER_SECONDS
                )

            )


            freshness = self._clip01(

                1.0

                -

                seconds_since_last_tick

                /

                max(

                    float(
                        CONFIG.DATA_STALE_AFTER_SECONDS
                    )
                    * 2.0,

                    1e-9,

                )

            )



        reconnect_penalty = min(

            self.connector.reconnect_count
            /
            10.0,

            0.50,

        )



        data_quality = self._clip01(

            freshness

            *

            (

                1.0

                -

                reconnect_penalty

            )

        )



        context = {


            "data_stale":
                data_stale,


            "seconds_since_last_tick":
                seconds_since_last_tick,


            "reconnect_count":
                self.connector.reconnect_count,


            "data_quality_score":
                data_quality,

        }



        context.update(
            self.learning.runtime_context()
        )


        return context





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
    def _build_logger() -> logging.Logger:

        logger = logging.getLogger(
            "personal_ai_trading_analyst"
        )


        level = getattr(

            logging,

            str(
                CONFIG.LOG_LEVEL
            ).upper(),

            logging.INFO,

        )


        logger.setLevel(
            level
        )


        logger.propagate = False



        if logger.handlers:

            return logger



        log_path = (
            CONFIG.LOG_DIR
            /
            "analyst.log"
        )


        handler = RotatingFileHandler(

            log_path,

            maxBytes=5_000_000,

            backupCount=3,

            encoding="utf-8",

        )


        formatter = logging.Formatter(

            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

        )


        handler.setFormatter(
            formatter
        )


        logger.addHandler(
            handler
        )


        return logger



# ============================================================
# END PART 7/7
# File Complete
# ============================================================