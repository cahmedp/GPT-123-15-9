from __future__ import annotations

from typing import Mapping

from config import CONFIG
from agents.trend_agent import AgentOpinion
from intelligence.market_intelligence import MarketIntelligenceSnapshot
from intelligence.pattern_engine import PatternSnapshot, PatternSignal
from intelligence.regime_detector import RegimeSnapshot


class PatternAgent:
    """
    Pattern specialist.

    Focus:
    - compression,
    - wick clusters,
    - rejection,
    - fake breaks,
    - real breakouts,
    - breakout + retest,
    - expansion,
    - pattern agreement/conflict across 30s, 1m and 5m.

    It produces an opinion only.
    It never executes trades.
    """

    NAME = "pattern_agent"

    _TF_WEIGHTS = {
        CONFIG.BASE_TIMEFRAME_SECONDS: 0.25,
        CONFIG.TIMEFRAME_1M_SECONDS: 0.35,
        CONFIG.TIMEFRAME_5M_SECONDS: 0.40,
    }

    _PATTERN_WEIGHTS = {
        "fake_break": 0.22,
        "breakout_retest": 0.20,
        "breakout": 0.16,
        "rejection": 0.14,
        "wick_cluster": 0.12,
        "expansion": 0.10,
        "compression": 0.06,
    }

    def evaluate(
        self,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
    ) -> AgentOpinion:

        timeframe_scores: dict[int, float] = {}
        timeframe_quality: dict[int, float] = {}
        timeframe_conflict: dict[int, float] = {}

        for timeframe in (
            CONFIG.BASE_TIMEFRAME_SECONDS,
            CONFIG.TIMEFRAME_1M_SECONDS,
            CONFIG.TIMEFRAME_5M_SECONDS,
        ):
            snapshot = patterns_by_timeframe.get(timeframe)

            score, quality, conflict = self._score_timeframe(
                snapshot
            )

            timeframe_scores[timeframe] = score
            timeframe_quality[timeframe] = quality
            timeframe_conflict[timeframe] = conflict

        raw_score = sum(
            timeframe_scores[tf]
            * self._TF_WEIGHTS[tf]
            for tf in self._TF_WEIGHTS
        )

        pattern_quality = self._weighted_average(
            timeframe_quality
        )

        internal_conflict = self._weighted_average(
            timeframe_conflict
        )

        cross_timeframe_conflict = self._cross_timeframe_conflict(
            timeframe_scores
        )

        conflict = self._clip01(
            0.55 * internal_conflict
            + 0.45 * cross_timeframe_conflict
        )

        regime_adjustment = self._regime_adjustment(
            regime
        )

        sequence_bonus = self._sequence_bonus(
            patterns_by_timeframe
        )

        market_alignment_bonus = (
            (market.alignment_score - 0.50) * 0.20
        )

        score = self._clip(
            raw_score
            + regime_adjustment
            + sequence_bonus
            + market_alignment_bonus,
            -1.0,
            1.0,
        )

        dominant_signal = self._dominant_signal(
            patterns_by_timeframe
        )

        dominant_strength = (
            self._signal_strength(dominant_signal)
            if dominant_signal is not None
            else 0.0
        )

        confirmation_score = self._confirmation_score(
            patterns_by_timeframe=patterns_by_timeframe,
            score=score,
        )

        noise_penalty = self._clip01(
            0.50 * market.noise_score
            + 0.30 * regime.noise_strength
            + 0.20 * conflict
        )

        confidence = self._clip01(
            (
                0.30 * abs(score)
                + 0.25 * pattern_quality
                + 0.20 * dominant_strength
                + 0.15 * confirmation_score
                + 0.10 * market.alignment_score
            )
            * (1.0 - 0.65 * noise_penalty)
            * (1.0 - 0.50 * conflict)
        )

        uncertainty = self._clip01(
            0.35 * conflict
            + 0.25 * noise_penalty
            + 0.20 * (1.0 - pattern_quality)
            + 0.20 * (1.0 - confirmation_score)
        )

        direction = self._direction(
            score=score,
            confidence=confidence,
        )

        veto = self._should_veto(
            market=market,
            regime=regime,
            direction=direction,
            confidence=confidence,
            uncertainty=uncertainty,
            conflict=conflict,
            patterns_by_timeframe=patterns_by_timeframe,
        )

        reasons = self._build_reasons(
            market=market,
            regime=regime,
            patterns_by_timeframe=patterns_by_timeframe,
            timeframe_scores=timeframe_scores,
            score=score,
            direction=direction,
            confidence=confidence,
            conflict=conflict,
            pattern_quality=pattern_quality,
            confirmation_score=confirmation_score,
            dominant_signal=dominant_signal,
            veto=veto,
        )

        evidence = {
            "score_30s": round(
                timeframe_scores[
                    CONFIG.BASE_TIMEFRAME_SECONDS
                ],
                6,
            ),
            "score_1m": round(
                timeframe_scores[
                    CONFIG.TIMEFRAME_1M_SECONDS
                ],
                6,
            ),
            "score_5m": round(
                timeframe_scores[
                    CONFIG.TIMEFRAME_5M_SECONDS
                ],
                6,
            ),
            "pattern_quality": round(
                pattern_quality,
                6,
            ),
            "internal_conflict": round(
                internal_conflict,
                6,
            ),
            "cross_timeframe_conflict": round(
                cross_timeframe_conflict,
                6,
            ),
            "confirmation_score": round(
                confirmation_score,
                6,
            ),
            "sequence_bonus": round(
                sequence_bonus,
                6,
            ),
            "regime_adjustment": round(
                regime_adjustment,
                6,
            ),
            "dominant_pattern": (
                dominant_signal.name
                if dominant_signal is not None
                else None
            ),
            "dominant_pattern_direction": (
                dominant_signal.direction
                if dominant_signal is not None
                else None
            ),
            "regime": regime.primary_regime,
        }

        return AgentOpinion(
            agent=self.NAME,
            direction=direction,
            score=float(score),
            confidence=float(confidence),
            uncertainty=float(uncertainty),
            veto=bool(veto),
            reasons=tuple(reasons),
            evidence=evidence,
        )

    def _score_timeframe(
        self,
        snapshot: PatternSnapshot | None,
    ) -> tuple[float, float, float]:
        if snapshot is None:
            return 0.0, 0.0, 0.0

        score = 0.0

        for attribute, weight in self._PATTERN_WEIGHTS.items():
            signal = getattr(
                snapshot,
                attribute,
                None,
            )

            score += self._signed_signal_score(
                signal=signal,
                weight=weight,
            )

        score = self._clip(
            score,
            -1.0,
            1.0,
        )

        quality = self._clip01(
            snapshot.pattern_quality
        )

        conflict = self._clip01(
            snapshot.conflict_score
        )

        return score, quality, conflict

    @classmethod
    def _signed_signal_score(
        cls,
        signal: PatternSignal | None,
        weight: float,
    ) -> float:
        if signal is None:
            return 0.0

        if signal.direction == "BULLISH":
            sign = 1.0
        elif signal.direction == "BEARISH":
            sign = -1.0
        else:
            return 0.0

        stage_multiplier = {
            "CONFIRMED": 1.0,
            "BUILDING": 0.65,
            "FAILED": 0.0,
        }.get(
            signal.stage,
            0.50,
        )

        strength = (
            (signal.score / 100.0)
            * signal.confidence
            * stage_multiplier
        )

        return float(
            sign
            * strength
            * weight
        )

    @classmethod
    def _signal_strength(
        cls,
        signal: PatternSignal | None,
    ) -> float:
        if signal is None:
            return 0.0

        stage_multiplier = {
            "CONFIRMED": 1.0,
            "BUILDING": 0.65,
            "FAILED": 0.0,
        }.get(
            signal.stage,
            0.50,
        )

        return cls._clip01(
            (signal.score / 100.0)
            * signal.confidence
            * stage_multiplier
        )

    @classmethod
    def _dominant_signal(
        cls,
        snapshots: Mapping[int, PatternSnapshot],
    ) -> PatternSignal | None:
        candidates: list[
            tuple[float, PatternSignal]
        ] = []

        for timeframe, snapshot in snapshots.items():
            tf_weight = cls._TF_WEIGHTS.get(
                timeframe,
                0.20,
            )

            for signal in snapshot.all_patterns:
                if signal.direction == "NEUTRAL":
                    continue

                pattern_weight = cls._PATTERN_WEIGHTS.get(
                    cls._attribute_name_from_signal(
                        signal.name
                    ),
                    0.08,
                )

                strength = (
                    cls._signal_strength(signal)
                    * tf_weight
                    * pattern_weight
                )

                candidates.append(
                    (
                        strength,
                        signal,
                    )
                )

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: item[0],
        )[1]

    @classmethod
    def _confirmation_score(
        cls,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
        score: float,
    ) -> float:
        if abs(score) < 0.10:
            return 0.0

        expected_direction = (
            "BULLISH"
            if score > 0
            else "BEARISH"
        )

        confirmed_weight = 0.0
        available_weight = 0.0

        for timeframe, tf_weight in cls._TF_WEIGHTS.items():
            snapshot = patterns_by_timeframe.get(
                timeframe
            )

            if snapshot is None:
                continue

            available_weight += tf_weight

            best_strength = 0.0

            for signal in snapshot.all_patterns:
                if (
                    signal.direction
                    != expected_direction
                ):
                    continue

                best_strength = max(
                    best_strength,
                    cls._signal_strength(signal),
                )

            confirmed_weight += (
                best_strength
                * tf_weight
            )

        if available_weight <= 0:
            return 0.0

        return cls._clip01(
            confirmed_weight
            / available_weight
        )

    @classmethod
    def _sequence_bonus(
        cls,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
    ) -> float:
        """
        Rewards coherent sequences such as:
            compression -> breakout -> retest -> expansion

        and:
            wick cluster -> fake break -> rejection

        Direction of the bonus follows the confirmed directional signal.
        """

        bullish_bonus = 0.0
        bearish_bonus = 0.0

        for timeframe, snapshot in patterns_by_timeframe.items():
            weight = cls._TF_WEIGHTS.get(
                timeframe,
                0.20,
            )

            compression = (
                snapshot.compression
                is not None
            )

            breakout = snapshot.breakout
            retest = snapshot.breakout_retest
            expansion = snapshot.expansion
            fake_break = snapshot.fake_break
            rejection = snapshot.rejection
            wick_cluster = snapshot.wick_cluster

            if compression and breakout is not None:
                direction = breakout.direction

                bonus = (
                    0.04
                    * cls._signal_strength(
                        breakout
                    )
                    * weight
                )

                if direction == "BULLISH":
                    bullish_bonus += bonus
                elif direction == "BEARISH":
                    bearish_bonus += bonus

            if (
                breakout is not None
                and retest is not None
                and breakout.direction
                == retest.direction
            ):
                bonus = (
                    0.08
                    * min(
                        cls._signal_strength(
                            breakout
                        ),
                        cls._signal_strength(
                            retest
                        ),
                    )
                    * weight
                )

                if breakout.direction == "BULLISH":
                    bullish_bonus += bonus
                elif breakout.direction == "BEARISH":
                    bearish_bonus += bonus

            if (
                retest is not None
                and expansion is not None
                and retest.direction
                == expansion.direction
            ):
                bonus = (
                    0.07
                    * min(
                        cls._signal_strength(
                            retest
                        ),
                        cls._signal_strength(
                            expansion
                        ),
                    )
                    * weight
                )

                if retest.direction == "BULLISH":
                    bullish_bonus += bonus
                elif retest.direction == "BEARISH":
                    bearish_bonus += bonus

            if (
                fake_break is not None
                and rejection is not None
                and fake_break.direction
                == rejection.direction
            ):
                bonus = (
                    0.08
                    * min(
                        cls._signal_strength(
                            fake_break
                        ),
                        cls._signal_strength(
                            rejection
                        ),
                    )
                    * weight
                )

                if fake_break.direction == "BULLISH":
                    bullish_bonus += bonus
                elif fake_break.direction == "BEARISH":
                    bearish_bonus += bonus

            if (
                wick_cluster is not None
                and fake_break is not None
                and wick_cluster.direction
                == fake_break.direction
            ):
                bonus = (
                    0.05
                    * min(
                        cls._signal_strength(
                            wick_cluster
                        ),
                        cls._signal_strength(
                            fake_break
                        ),
                    )
                    * weight
                )

                if fake_break.direction == "BULLISH":
                    bullish_bonus += bonus
                elif fake_break.direction == "BEARISH":
                    bearish_bonus += bonus

        return cls._clip(
            bullish_bonus
            - bearish_bonus,
            -0.20,
            0.20,
        )

    @classmethod
    def _regime_adjustment(
        cls,
        regime: RegimeSnapshot,
    ) -> float:
        confidence = cls._clip01(
            regime.regime_confidence
        )

        if regime.primary_regime in {
            "BULLISH_TREND",
            "BULLISH_EXPANSION",
        }:
            return (
                0.08
                * confidence
            )

        if regime.primary_regime in {
            "BEARISH_TREND",
            "BEARISH_EXPANSION",
        }:
            return (
                -0.08
                * confidence
            )

        if regime.primary_regime in {
            "HIGH_NOISE",
            "TRANSITION",
        }:
            return 0.0

        return (
            regime.directional_bias
            * 0.03
        )

    @classmethod
    def _weighted_average(
        cls,
        values: Mapping[int, float],
    ) -> float:
        total = 0.0
        weight_total = 0.0

        for timeframe, weight in cls._TF_WEIGHTS.items():
            if timeframe not in values:
                continue

            total += (
                float(values[timeframe])
                * weight
            )
            weight_total += weight

        if weight_total <= 0:
            return 0.0

        return cls._clip01(
            total / weight_total
        )

    @classmethod
    def _cross_timeframe_conflict(
        cls,
        timeframe_scores: Mapping[int, float],
    ) -> float:
        bullish = 0.0
        bearish = 0.0

        for timeframe, score in timeframe_scores.items():
            weight = cls._TF_WEIGHTS.get(
                timeframe,
                0.20,
            )

            if score > 0:
                bullish += (
                    score * weight
                )
            elif score < 0:
                bearish += (
                    -score * weight
                )

        total = bullish + bearish

        if total <= 1e-12:
            return 0.0

        return cls._clip01(
            (
                2.0
                * min(
                    bullish,
                    bearish,
                )
            )
            / total
        )

    @classmethod
    def _should_veto(
        cls,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        direction: str,
        confidence: float,
        uncertainty: float,
        conflict: float,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
    ) -> bool:

        if market.readiness_state in {
            "WARMUP",
            "BLOCKED_NOISE",
        }:
            return True

        if regime.primary_regime == "HIGH_NOISE":
            return True

        if conflict >= 0.75:
            return True

        if uncertainty >= 0.80:
            return True

        if (
            direction == "WAIT"
            and confidence < 0.30
        ):
            return True

        # Opposing confirmed high-quality breakouts on different timeframes
        # are treated as unresolved conflict.
        breakout_directions = {
            snapshot.breakout.direction
            for snapshot in patterns_by_timeframe.values()
            if snapshot.breakout is not None
            and snapshot.breakout.stage == "CONFIRMED"
            and snapshot.breakout.confidence >= 0.70
            and snapshot.breakout.direction
            in {"BULLISH", "BEARISH"}
        }

        if len(breakout_directions) > 1:
            return True

        # Same protection for strong fake-break signals.
        fake_break_directions = {
            snapshot.fake_break.direction
            for snapshot in patterns_by_timeframe.values()
            if snapshot.fake_break is not None
            and snapshot.fake_break.stage == "CONFIRMED"
            and snapshot.fake_break.confidence >= 0.70
            and snapshot.fake_break.direction
            in {"BULLISH", "BEARISH"}
        }

        if len(fake_break_directions) > 1:
            return True

        return False

    @staticmethod
    def _direction(
        score: float,
        confidence: float,
    ) -> str:
        if (
            confidence
            < CONFIG.AGENT_MIN_CONFIDENCE
            or abs(score) < 0.18
        ):
            return "WAIT"

        return (
            "BULLISH"
            if score > 0
            else "BEARISH"
        )

    @classmethod
    def _build_reasons(
        cls,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
        timeframe_scores: Mapping[int, float],
        score: float,
        direction: str,
        confidence: float,
        conflict: float,
        pattern_quality: float,
        confirmation_score: float,
        dominant_signal: PatternSignal | None,
        veto: bool,
    ) -> list[str]:
        reasons: list[str] = []

        if dominant_signal is not None:
            reasons.append(
                f"dominant pattern: "
                f"{dominant_signal.name.lower()} "
                f"({dominant_signal.direction.lower()})"
            )

        for timeframe, label in (
            (
                CONFIG.TIMEFRAME_5M_SECONDS,
                "5m",
            ),
            (
                CONFIG.TIMEFRAME_1M_SECONDS,
                "1m",
            ),
            (
                CONFIG.BASE_TIMEFRAME_SECONDS,
                "30s",
            ),
        ):
            tf_score = timeframe_scores.get(
                timeframe,
                0.0,
            )

            if tf_score >= 0.18:
                reasons.append(
                    f"{label} pattern evidence is bullish"
                )
            elif tf_score <= -0.18:
                reasons.append(
                    f"{label} pattern evidence is bearish"
                )

        if confirmation_score >= 0.60:
            reasons.append(
                "patterns confirm each other across timeframes"
            )

        if pattern_quality >= 0.60:
            reasons.append(
                "pattern quality is strong"
            )

        if conflict >= 0.55:
            reasons.append(
                "pattern conflict is elevated"
            )

        if (
            market.compression_pressure >= 0.65
        ):
            reasons.append(
                "compression pressure is elevated"
            )

        if (
            market.expansion_potential >= 0.65
        ):
            reasons.append(
                "expansion potential is elevated"
            )

        if regime.primary_regime in {
            "BULLISH_EXPANSION",
            "BEARISH_EXPANSION",
        }:
            reasons.append(
                f"regime supports expansion: "
                f"{regime.primary_regime.lower()}"
            )

        if direction == "WAIT":
            reasons.append(
                f"pattern evidence is not decisive "
                f"(score={score:.2f}, confidence={confidence:.2f})"
            )

        if veto:
            reasons.append(
                "pattern agent requests a safety veto"
            )

        return reasons

    @staticmethod
    def _attribute_name_from_signal(
        name: str,
    ) -> str:
        mapping = {
            "COMPRESSION": "compression",
            "WICK_CLUSTER": "wick_cluster",
            "REJECTION": "rejection",
            "FAKE_BREAK": "fake_break",
            "BREAKOUT": "breakout",
            "BREAKOUT_RETEST": "breakout_retest",
            "EXPANSION": "expansion",
        }

        return mapping.get(
            name,
            name.lower(),
        )

    @staticmethod
    def _clip01(value: float) -> float:
        return min(
            max(float(value), 0.0),
            1.0,
        )

    @staticmethod
    def _clip(
        value: float,
        low: float,
        high: float,
    ) -> float:
        return min(
            max(float(value), low),
            high,
        )
