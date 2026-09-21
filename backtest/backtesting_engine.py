from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

from config import CONFIG


@dataclass(frozen=True, slots=True)
class BacktestSignal:
    """
    Normalized advisory signal returned by the strategy callback.

    action:
        BUY | SELL | WAIT
    """

    action: str
    confidence: float
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BacktestCase:
    timestamp: float
    entry_price: float
    exit_timestamp: float
    exit_price: float

    action: str
    confidence: float

    actual_direction: str
    correct: Optional[bool]

    move: float
    move_fraction: float

    split: str

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "entry_price": self.entry_price,
            "exit_timestamp": self.exit_timestamp,
            "exit_price": self.exit_price,
            "action": self.action,
            "confidence": self.confidence,
            "actual_direction": self.actual_direction,
            "correct": self.correct,
            "move": self.move,
            "move_fraction": self.move_fraction,
            "split": self.split,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    total_cases: int
    directional_calls: int
    waits: int

    wins: int
    losses: int
    neutral: int

    accuracy: Optional[float]
    coverage: float
    wait_rate: float

    average_confidence: Optional[float]
    average_winner_confidence: Optional[float]
    average_loser_confidence: Optional[float]

    high_confidence_calls: int
    high_confidence_accuracy: Optional[float]

    calibration_error: Optional[float]

    bullish_calls: int
    bearish_calls: int

    bullish_accuracy: Optional[float]
    bearish_accuracy: Optional[float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "directional_calls": self.directional_calls,
            "waits": self.waits,
            "wins": self.wins,
            "losses": self.losses,
            "neutral": self.neutral,
            "accuracy": self.accuracy,
            "coverage": self.coverage,
            "wait_rate": self.wait_rate,
            "average_confidence": self.average_confidence,
            "average_winner_confidence": self.average_winner_confidence,
            "average_loser_confidence": self.average_loser_confidence,
            "high_confidence_calls": self.high_confidence_calls,
            "high_confidence_accuracy": self.high_confidence_accuracy,
            "calibration_error": self.calibration_error,
            "bullish_calls": self.bullish_calls,
            "bearish_calls": self.bearish_calls,
            "bullish_accuracy": self.bullish_accuracy,
            "bearish_accuracy": self.bearish_accuracy,
        }


@dataclass(frozen=True, slots=True)
class BacktestResult:
    asset: str
    timeframe_seconds: int
    expiry_seconds: int

    total_input_candles: int

    train_metrics: BacktestMetrics
    validation_metrics: BacktestMetrics
    test_metrics: BacktestMetrics
    overall_metrics: BacktestMetrics

    cases: tuple[BacktestCase, ...] = field(default_factory=tuple)

    leakage_safe: bool = True

    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset,
            "timeframe_seconds": self.timeframe_seconds,
            "expiry_seconds": self.expiry_seconds,
            "total_input_candles": self.total_input_candles,
            "train_metrics": self.train_metrics.as_dict(),
            "validation_metrics": self.validation_metrics.as_dict(),
            "test_metrics": self.test_metrics.as_dict(),
            "overall_metrics": self.overall_metrics.as_dict(),
            "cases": [
                case.as_dict()
                for case in self.cases
            ],
            "leakage_safe": self.leakage_safe,
            "notes": list(self.notes),
        }


StrategyCallback = Callable[
    [Sequence[Any]],
    BacktestSignal | Mapping[str, Any] | str,
]


class BacktestingEngine:
    """
    Leakage-safe historical backtesting engine.

    The strategy callback receives ONLY candles available up to the current
    decision candle. Future candles are hidden from the callback.

    Evaluation:
        BUY  -> correct when future close > entry close
        SELL -> correct when future close < entry close
        WAIT -> no directional win/loss assigned
        equal future close -> neutral result

    This engine intentionally measures analytical quality rather than
    pretending a specific broker payout/return model.

    Typical use:
        result = engine.run(
            candles=candles,
            strategy=my_strategy,
            asset="GBPUSD_OTC",
            timeframe_seconds=30,
            expiry_seconds=30,
        )
    """

    def run(
        self,
        *,
        candles: Sequence[Any],
        strategy: StrategyCallback,
        asset: str = CONFIG.PAIR,
        timeframe_seconds: int = CONFIG.BASE_TIMEFRAME_SECONDS,
        expiry_seconds: Optional[int] = None,
        warmup_candles: Optional[int] = None,
    ) -> BacktestResult:
        if timeframe_seconds <= 0:
            raise ValueError(
                "timeframe_seconds must be positive."
            )

        expiry_seconds = int(
            expiry_seconds
            if expiry_seconds is not None
            else timeframe_seconds
        )

        if expiry_seconds <= 0:
            raise ValueError(
                "expiry_seconds must be positive."
            )

        minimum_required = int(
            getattr(
                CONFIG,
                "BACKTEST_MIN_CASES",
                500,
            )
        )

        normalized = self._normalize_candles(
            candles
        )

        if len(normalized) < minimum_required:
            raise ValueError(
                f"Backtest requires at least {minimum_required} candles; "
                f"received {len(normalized)}."
            )

        warmup = int(
            warmup_candles
            if warmup_candles is not None
            else max(
                int(
                    getattr(
                        CONFIG,
                        "MIN_BASE_CANDLES",
                        120,
                    )
                ),
                50,
            )
        )

        if warmup < 1:
            warmup = 1

        expiry_steps = max(
            1,
            int(
                round(
                    expiry_seconds
                    / timeframe_seconds
                )
            ),
        )

        usable_end = (
            len(normalized)
            - expiry_steps
        )

        if usable_end <= warmup:
            raise ValueError(
                "Not enough candles remain after warmup and expiry horizon."
            )

        train_ratio = self._config_ratio(
            "BACKTEST_TRAIN_RATIO",
            0.70,
        )
        validation_ratio = self._config_ratio(
            "BACKTEST_VALIDATION_RATIO",
            0.15,
        )
        test_ratio = self._config_ratio(
            "BACKTEST_TEST_RATIO",
            0.15,
        )

        total_ratio = (
            train_ratio
            + validation_ratio
            + test_ratio
        )

        if total_ratio <= 0:
            raise ValueError(
                "Backtest split ratios must have positive total."
            )

        train_ratio /= total_ratio
        validation_ratio /= total_ratio
        test_ratio /= total_ratio

        evaluation_count = (
            usable_end
            - warmup
        )

        train_end_offset = int(
            evaluation_count
            * train_ratio
        )

        validation_end_offset = int(
            evaluation_count
            * (
                train_ratio
                + validation_ratio
            )
        )

        cases: list[
            BacktestCase
        ] = []

        for offset, index in enumerate(
            range(
                warmup,
                usable_end,
            )
        ):
            history = normalized[
                :index + 1
            ]

            raw_signal = strategy(
                history
            )

            signal = self._normalize_signal(
                raw_signal
            )

            entry = normalized[
                index
            ]

            exit_candle = normalized[
                index
                + expiry_steps
            ]

            split = self._split_name(
                offset=offset,
                train_end_offset=train_end_offset,
                validation_end_offset=validation_end_offset,
            )

            case = self._evaluate_case(
                entry=entry,
                exit_candle=exit_candle,
                signal=signal,
                split=split,
            )

            cases.append(
                case
            )

        train_cases = [
            case
            for case in cases
            if case.split == "TRAIN"
        ]

        validation_cases = [
            case
            for case in cases
            if case.split == "VALIDATION"
        ]

        test_cases = [
            case
            for case in cases
            if case.split == "TEST"
        ]

        notes = [
            "strategy callback received past/current candles only",
            "future outcome candles were used only after each signal was produced",
            "WAIT decisions are excluded from directional accuracy",
            "no broker payout assumptions are included",
        ]

        if not test_cases:
            notes.append(
                "test split contained no evaluable cases"
            )

        return BacktestResult(
            asset=str(asset),
            timeframe_seconds=int(
                timeframe_seconds
            ),
            expiry_seconds=int(
                expiry_seconds
            ),

            total_input_candles=len(
                normalized
            ),

            train_metrics=self._metrics(
                train_cases
            ),
            validation_metrics=self._metrics(
                validation_cases
            ),
            test_metrics=self._metrics(
                test_cases
            ),
            overall_metrics=self._metrics(
                cases
            ),

            cases=tuple(cases),

            leakage_safe=True,

            notes=tuple(notes),
        )

    def walk_forward(
        self,
        *,
        candles: Sequence[Any],
        strategy: StrategyCallback,
        asset: str = CONFIG.PAIR,
        timeframe_seconds: int = CONFIG.BASE_TIMEFRAME_SECONDS,
        expiry_seconds: Optional[int] = None,
        initial_train_size: Optional[int] = None,
        test_window_size: int = 200,
    ) -> list[BacktestResult]:
        """
        Expanding-window walk-forward evaluation.

        Each round uses:
            all historical data up to the window
            -> test only on the next unseen window.

        This is useful later for champion/challenger validation.
        """

        normalized = self._normalize_candles(
            candles
        )

        expiry_seconds = int(
            expiry_seconds
            if expiry_seconds is not None
            else timeframe_seconds
        )

        initial_train = int(
            initial_train_size
            if initial_train_size is not None
            else max(
                self._config_int(
                    "BACKTEST_MIN_CASES",
                    500,
                ),
                500,
            )
        )

        if test_window_size <= 0:
            raise ValueError(
                "test_window_size must be positive."
            )

        if len(normalized) <= initial_train:
            return []

        results: list[
            BacktestResult
        ] = []

        end = (
            initial_train
            + test_window_size
        )

        while end <= len(
            normalized
        ):
            subset = normalized[
                :end
            ]

            # The normal run remains leakage-safe and produces train/val/test
            # metrics. The last test segment is the unseen walk-forward window.
            try:
                result = self.run(
                    candles=subset,
                    strategy=strategy,
                    asset=asset,
                    timeframe_seconds=timeframe_seconds,
                    expiry_seconds=expiry_seconds,
                )
            except ValueError:
                break

            results.append(
                result
            )

            end += test_window_size

        return results

    @staticmethod
    def _normalize_candles(
        candles: Sequence[Any],
    ) -> list[Any]:
        required = (
            "timestamp",
            "open",
            "high",
            "low",
            "close",
        )

        valid: list[
            Any
        ] = []

        for candle in candles:
            if not all(
                hasattr(
                    candle,
                    field
                )
                for field in required
            ):
                raise TypeError(
                    "Each candle must expose timestamp/open/high/low/close."
                )

            timestamp = float(
                candle.timestamp
            )

            open_price = float(
                candle.open
            )
            high = float(
                candle.high
            )
            low = float(
                candle.low
            )
            close = float(
                candle.close
            )

            if timestamp <= 0:
                continue

            if min(
                open_price,
                high,
                low,
                close,
            ) <= 0:
                continue

            valid.append(
                candle
            )

        valid.sort(
            key=lambda candle: float(
                candle.timestamp
            )
        )

        deduplicated: list[
            Any
        ] = []

        last_timestamp: Optional[
            float
        ] = None

        for candle in valid:
            timestamp = float(
                candle.timestamp
            )

            if (
                last_timestamp is not None
                and timestamp
                == last_timestamp
            ):
                # Keep the last representation of a duplicated timestamp.
                deduplicated[
                    -1
                ] = candle
            else:
                deduplicated.append(
                    candle
                )
                last_timestamp = timestamp

        return deduplicated

    @classmethod
    def _normalize_signal(
        cls,
        raw: BacktestSignal | Mapping[str, Any] | str,
    ) -> BacktestSignal:
        if isinstance(
            raw,
            BacktestSignal,
        ):
            action = raw.action
            confidence = raw.confidence
            metadata = raw.metadata

        elif isinstance(
            raw,
            str,
        ):
            action = raw
            confidence = 0.50
            metadata = {}

        elif isinstance(
            raw,
            Mapping,
        ):
            action = str(
                raw.get(
                    "action",
                    raw.get(
                        "advisory_action",
                        "WAIT",
                    ),
                )
            )

            confidence = cls._safe_float(
                raw.get(
                    "confidence",
                    raw.get(
                        "calibrated_confidence",
                        0.50,
                    ),
                ),
                0.50,
            )

            metadata = {
                key: value
                for key, value
                in raw.items()
                if key
                not in {
                    "action",
                    "advisory_action",
                    "confidence",
                    "calibrated_confidence",
                }
            }

        else:
            raise TypeError(
                "Strategy must return BacktestSignal, mapping, or string."
            )

        action = str(
            action
        ).strip().upper()

        if action not in {
            "BUY",
            "SELL",
            "WAIT",
        }:
            action = "WAIT"

        return BacktestSignal(
            action=action,
            confidence=cls._clip01(
                confidence
            ),
            metadata=dict(
                metadata
            ),
        )

    @classmethod
    def _evaluate_case(
        cls,
        *,
        entry: Any,
        exit_candle: Any,
        signal: BacktestSignal,
        split: str,
    ) -> BacktestCase:
        entry_price = float(
            entry.close
        )

        exit_price = float(
            exit_candle.close
        )

        move = (
            exit_price
            - entry_price
        )

        move_fraction = (
            move
            / entry_price
            if entry_price != 0
            else 0.0
        )

        if move > 0:
            actual_direction = "BULLISH"
        elif move < 0:
            actual_direction = "BEARISH"
        else:
            actual_direction = "NEUTRAL"

        if signal.action == "WAIT":
            correct: Optional[
                bool
            ] = None

        elif actual_direction == "NEUTRAL":
            correct = None

        elif signal.action == "BUY":
            correct = (
                actual_direction
                == "BULLISH"
            )

        else:
            correct = (
                actual_direction
                == "BEARISH"
            )

        return BacktestCase(
            timestamp=float(
                entry.timestamp
            ),
            entry_price=entry_price,

            exit_timestamp=float(
                exit_candle.timestamp
            ),
            exit_price=exit_price,

            action=signal.action,
            confidence=float(
                signal.confidence
            ),

            actual_direction=actual_direction,
            correct=correct,

            move=float(
                move
            ),
            move_fraction=float(
                move_fraction
            ),

            split=split,

            metadata=dict(
                signal.metadata
            ),
        )

    @classmethod
    def _metrics(
        cls,
        cases: Sequence[BacktestCase],
    ) -> BacktestMetrics:
        total = len(cases)

        directional = [
            case
            for case in cases
            if case.action
            in {
                "BUY",
                "SELL",
            }
        ]

        evaluable = [
            case
            for case in directional
            if case.correct
            is not None
        ]

        wins = sum(
            1
            for case in evaluable
            if case.correct is True
        )

        losses = sum(
            1
            for case in evaluable
            if case.correct is False
        )

        neutral = (
            len(directional)
            - len(evaluable)
        )

        waits = sum(
            1
            for case in cases
            if case.action == "WAIT"
        )

        bullish = [
            case
            for case in evaluable
            if case.action == "BUY"
        ]

        bearish = [
            case
            for case in evaluable
            if case.action == "SELL"
        ]

        winners = [
            case
            for case in evaluable
            if case.correct is True
        ]

        losers = [
            case
            for case in evaluable
            if case.correct is False
        ]

        strong_threshold = cls._config_float(
            "STRONG_ADVISORY_CONFIDENCE",
            0.82,
        )

        high_confidence = [
            case
            for case in evaluable
            if case.confidence
            >= strong_threshold
        ]

        return BacktestMetrics(
            total_cases=total,
            directional_calls=len(
                directional
            ),
            waits=waits,

            wins=wins,
            losses=losses,
            neutral=neutral,

            accuracy=cls._accuracy(
                evaluable
            ),

            coverage=(
                len(directional)
                / total
                if total
                else 0.0
            ),

            wait_rate=(
                waits
                / total
                if total
                else 0.0
            ),

            average_confidence=cls._average_confidence(
                evaluable
            ),

            average_winner_confidence=cls._average_confidence(
                winners
            ),

            average_loser_confidence=cls._average_confidence(
                losers
            ),

            high_confidence_calls=len(
                high_confidence
            ),

            high_confidence_accuracy=cls._accuracy(
                high_confidence
            ),

            calibration_error=cls._expected_calibration_error(
                evaluable
            ),

            bullish_calls=len(
                bullish
            ),
            bearish_calls=len(
                bearish
            ),

            bullish_accuracy=cls._accuracy(
                bullish
            ),
            bearish_accuracy=cls._accuracy(
                bearish
            ),
        )

    @staticmethod
    def _split_name(
        *,
        offset: int,
        train_end_offset: int,
        validation_end_offset: int,
    ) -> str:
        if offset < train_end_offset:
            return "TRAIN"

        if offset < validation_end_offset:
            return "VALIDATION"

        return "TEST"

    @staticmethod
    def _accuracy(
        cases: Sequence[BacktestCase],
    ) -> Optional[float]:
        valid = [
            case
            for case in cases
            if case.correct
            is not None
        ]

        if not valid:
            return None

        return (
            sum(
                1
                for case in valid
                if case.correct is True
            )
            / len(valid)
        )

    @staticmethod
    def _average_confidence(
        cases: Sequence[BacktestCase],
    ) -> Optional[float]:
        if not cases:
            return None

        return (
            sum(
                case.confidence
                for case in cases
            )
            / len(cases)
        )

    @classmethod
    def _expected_calibration_error(
        cls,
        cases: Sequence[BacktestCase],
        bins: int = 10,
    ) -> Optional[float]:
        valid = [
            case
            for case in cases
            if case.correct
            is not None
        ]

        if not valid:
            return None

        bins = max(
            int(bins),
            2,
        )

        total = len(
            valid
        )

        error = 0.0

        for bin_index in range(
            bins
        ):
            low = (
                bin_index
                / bins
            )

            high = (
                (
                    bin_index
                    + 1
                )
                / bins
            )

            if bin_index == (
                bins - 1
            ):
                group = [
                    case
                    for case in valid
                    if low
                    <= case.confidence
                    <= high
                ]
            else:
                group = [
                    case
                    for case in valid
                    if low
                    <= case.confidence
                    < high
                ]

            if not group:
                continue

            average_confidence = (
                sum(
                    case.confidence
                    for case in group
                )
                / len(group)
            )

            empirical_accuracy = (
                sum(
                    1.0
                    if case.correct is True
                    else 0.0
                    for case in group
                )
                / len(group)
            )

            error += (
                len(group)
                / total
            ) * abs(
                average_confidence
                - empirical_accuracy
            )

        return cls._clip01(
            error
        )

    @staticmethod
    def _config_ratio(
        name: str,
        default: float,
    ) -> float:
        try:
            value = float(
                getattr(
                    CONFIG,
                    name,
                    default,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            value = default

        return max(
            value,
            0.0,
        )

    @staticmethod
    def _config_int(
        name: str,
        default: int,
    ) -> int:
        try:
            return int(
                getattr(
                    CONFIG,
                    name,
                    default,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            return int(
                default
            )

    @staticmethod
    def _config_float(
        name: str,
        default: float,
    ) -> float:
        try:
            return float(
                getattr(
                    CONFIG,
                    name,
                    default,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            return float(
                default
            )

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            number = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return float(
                default
            )

        if number != number:
            return float(
                default
            )

        if number in {
            float("inf"),
            float("-inf"),
        }:
            return float(
                default
            )

        return number

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
