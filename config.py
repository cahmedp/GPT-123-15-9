from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AppConfig:
    # =========================================================
    # Application
    # =========================================================
    APP_NAME: str = "Personal AI Trading Analyst"
    APP_VERSION: str = "1.0.0"
    SYSTEM_MODE: str = "CONSULTANT"
    EXECUTION_ENABLED: bool = False

    # =========================================================
    # Market / Pocket Option
    # =========================================================
    PAIR: str = "GBPUSD_OTC"

    # Pocket Option naming can differ between endpoints/libraries.
    # The connector will resolve the first valid asset at runtime.
    POCKET_ASSET_CANDIDATES: Tuple[str, ...] = (
        "GBPUSD_otc",
        "GBPUSD_OTC",
        "GBPUSD-OTC",
        "GBPUSD",
    )

    # Manual startup only. No automatic daily scheduler.
    MAX_SESSION_HOURS: float = 8.0

    # =========================================================
    # Timeframes
    # =========================================================
    BASE_TIMEFRAME_SECONDS: int = 30
    TIMEFRAME_1M_SECONDS: int = 60
    TIMEFRAME_5M_SECONDS: int = 300

    # Minimum history needed before full reasoning begins.
    MIN_BASE_CANDLES: int = 300
    MAX_CANDLES_IN_MEMORY: int = 5000

    # =========================================================
    # Data / Stream
    # =========================================================
    STREAM_RECONNECT_DELAY_SECONDS: float = 2.0
    STREAM_MAX_RECONNECT_DELAY_SECONDS: float = 30.0
    DATA_STALE_AFTER_SECONDS: float = 8.0
    TICK_QUEUE_MAXSIZE: int = 5000
    CANDLE_QUEUE_MAXSIZE: int = 2000

    # Soft budget only; the connector will throttle rather than
    # consume the free API unnecessarily.
    API_SOFT_BUDGET_PER_SESSION: int = 5000
    API_WARNING_USAGE_RATIO: float = 0.80

    # =========================================================
    # Feature Engineering
    # =========================================================
    ATR_PERIOD: int = 14
    RSI_PERIOD: int = 7
    EMA_FAST_PERIOD: int = 9
    EMA_SLOW_PERIOD: int = 21
    STRUCTURE_LOOKBACK: int = 20
    SUPPORT_RESISTANCE_LOOKBACK: int = 50
    TICK_ACTIVITY_LOOKBACK: int = 20
    WICK_CLUSTER_LOOKBACK: int = 7

    # =========================================================
    # Market Intelligence / Regimes
    # =========================================================
    REGIME_LOOKBACK: int = 40
    COMPRESSION_LOOKBACK: int = 8
    COMPRESSION_RANGE_RATIO: float = 0.60
    EXPANSION_ATR_MULTIPLIER: float = 1.50
    NOISE_WICK_RATIO_THRESHOLD: float = 0.55
    TREND_STRENGTH_THRESHOLD: float = 0.60

    # =========================================================
    # Pattern Intelligence
    # =========================================================
    MIN_PATTERN_SCORE: float = 60.0
    MIN_CONFIRMATION_SCORE: float = 65.0
    LIQUIDITY_SWEEP_LOOKBACK: int = 12
    FAKE_BREAK_LOOKBACK: int = 12
    REJECTION_WICK_RATIO: float = 0.55
    STRONG_BODY_RATIO: float = 0.60

    # =========================================================
    # Multi-Agent Reasoning
    # =========================================================
    AGENT_MIN_CONFIDENCE: float = 0.50
    AGENT_CONFLICT_THRESHOLD: float = 0.35

    TREND_AGENT_WEIGHT: float = 0.20
    LIQUIDITY_AGENT_WEIGHT: float = 0.25
    PATTERN_AGENT_WEIGHT: float = 0.25
    RISK_AGENT_WEIGHT: float = 0.15
    MEMORY_AGENT_WEIGHT: float = 0.15

    # =========================================================
    # Decision Fusion / Confidence
    # =========================================================
    MIN_ADVISORY_CONFIDENCE: float = 0.60
    STRONG_ADVISORY_CONFIDENCE: float = 0.82
    MIN_SIMILAR_CASES_FOR_STRONG_MEMORY: int = 100
    MAX_UNCERTAINTY_FOR_DIRECTIONAL_ADVICE: float = 0.50

    # =========================================================
    # Risk
    # =========================================================
    MAX_ACCEPTABLE_RISK_SCORE: float = 0.60
    HIGH_NOISE_BLOCK_THRESHOLD: float = 0.75
    MAX_CONSECUTIVE_BAD_OUTCOMES: int = 3
    DEFENSIVE_MODE_CONFIDENCE_BONUS: float = 0.08

    # =========================================================
    # Memory / Knowledge
    # =========================================================
    MEMORY_DIR: Path = BASE_DIR / "storage" / "memory"
    JOURNAL_DIR: Path = BASE_DIR / "storage" / "journal"
    KNOWLEDGE_DIR: Path = BASE_DIR / "storage" / "knowledge"
    MODEL_DIR: Path = BASE_DIR / "storage" / "models"
    REPORT_DIR: Path = BASE_DIR / "storage" / "reports"
    LOG_DIR: Path = BASE_DIR / "storage" / "logs"

    MEMORY_MAX_SIMILAR_CASES: int = 250
    MEMORY_RECENCY_WEIGHT: float = 0.35
    MEMORY_SIMILARITY_WEIGHT: float = 0.40
    MEMORY_OUTCOME_WEIGHT: float = 0.25

    # =========================================================
    # Continuous Learning
    # =========================================================
    LEARNING_ENABLED: bool = True
    LEARNING_MIN_NEW_CASES: int = 100
    LEARNING_MIN_VALIDATION_CASES: int = 300
    LEARNING_MAX_WEIGHT_CHANGE_PER_UPDATE: float = 0.05
    CHAMPION_MIN_IMPROVEMENT: float = 0.02
    CHAMPION_MIN_TEST_CASES: int = 500

    # =========================================================
    # World Model / Simulation
    # =========================================================
    WORLD_MODEL_ENABLED: bool = True
    WORLD_MODEL_MAX_SCENARIOS: int = 200
    WORLD_MODEL_MIN_HISTORY: int = 300
    WORLD_MODEL_HORIZON_CANDLES: int = 4

    # =========================================================
    # Goal Manager
    # =========================================================
    GOAL_MANAGER_ENABLED: bool = True
    GOAL_REVIEW_INTERVAL_CASES: int = 200

    # =========================================================
    # Backtesting
    # =========================================================
    BACKTEST_TRAIN_RATIO: float = 0.70
    BACKTEST_VALIDATION_RATIO: float = 0.15
    BACKTEST_TEST_RATIO: float = 0.15
    BACKTEST_MIN_CASES: int = 500

    # =========================================================
    # Terminal Command Center
    # =========================================================
    UI_REFRESH_SECONDS: float = 1.0
    UI_SHOW_GLOW_STYLE: bool = True
    UI_MAX_EVENT_ROWS: int = 12
    UI_MAX_AGENT_ROWS: int = 8

    # =========================================================
    # Logging
    # =========================================================
    LOG_LEVEL: str = "INFO"
    LOG_JSONL: bool = True

    def ensure_directories(self) -> None:
        for path in (
            self.MEMORY_DIR,
            self.JOURNAL_DIR,
            self.KNOWLEDGE_DIR,
            self.MODEL_DIR,
            self.REPORT_DIR,
            self.LOG_DIR,
        ):
            path.mkdir(parents=True, exist_ok=True)


CONFIG = AppConfig()
CONFIG.ensure_directories()