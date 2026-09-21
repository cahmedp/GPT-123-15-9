from __future__ import annotations

from typing import Mapping

from config import CONFIG
from agents.trend_agent import AgentOpinion
from intelligence.market_intelligence import MarketIntelligenceSnapshot
from intelligence.pattern_engine import PatternSnapshot, PatternSignal
from intelligence.regime_detector import RegimeSnapshot


class LiquidityAgent:
    """
    Liquidity / manipulation specialist.

    Focus:
    - repeated wick clusters around the same area,
    - liquidity sweeps,
    - fake breaks,
    - rejection from support/resistance,
    - real breakout confirmation,
    - breakout + retest,
    - compression before expansion,
    - avoiding entries during unresolved liquidity conflict.

    The agent produces an opinion only.
    It never places orders.
    """

    NAME = "liquidity_agent"

    def evaluate(
        self,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
    ) -> AgentOpinion:
        p30 = patterns_by_timeframe.get(
            CONFIG.BASE_TIMEFRAME_SECONDS
        )
        p1m = patterns_by_timeframe.get(
            CONFIG.TIMEFRAME_1M_SECONDS
        )
        p5m = patterns_by_timeframe.get(
            CONFIG.TIMEFRAME_5M_SECONDS
        )

        score_30 = self._timeframe_liquidity_score(
            p30,
            weight_context=0.20,
        )
        score_1m = self._timeframe_liquidity_score(
            p1m,
            weight_context=0.35,
        )
        score_5m = self._timeframe_liquidity_score(
            p5m,
            weight_context=0.45,
        )

        raw_score = self._clip(
            score_30 + score_1m + score_5m,
            -1.0,
            1.0,
        )

        location_score = self._location_context_score(
            market
        )

        structure_score = self._structure_liquidity_score(
            market
        )

        regime_score = self._regime_score(
            regime
        )

        score = self._clip(
            (
                0.55 * raw_score
                + 0.20 * location_score
                + 0.15 * structure_score
                + 0.10 * regime_score
            ),
            -1.0,
            1.0,
        )

        liquidity_quality = self._liquidity_quality(
            p30=p30,
            p1m=p1m,
            p5m=p5m,
        )

        fake_break_strength = self._pattern_strength(
            patterns_by_timeframe,
            "fake_break",
        )

        retest_strength = self._pattern_strength(
            patterns_by_timeframe,
            "breakout_retest",
        )

        wick_cluster_strength = self._pattern_strength(
            patterns_by_timeframe,
            "wick_cluster",
        )

        rejection_strength = self._pattern_strength(
            patterns_by_timeframe,
            "rejection",
        )

        breakout_strength = self._pattern_strength(
            patterns_by_timeframe,
            "breakout",
        )

        compression_strength = self._pattern_strength(
            patterns_by_timeframe,
            "compression",
        )

        conflict = self._pattern_conflict(
            p30,
            p1m,
            p5m,
        )

        noise_penalty = self._clip01(
            0.55 * market.noise_score
            + 0.25 * regime.noise_strength
            + 0.20 * conflict
        )

        confirmation = self._clip01(
            0.22 * fake_break_strength
            + 0.20 * retest_strength
            + 0.18 * wick_cluster_strength
            + 0.18 * rejection_strength
            + 0.12 * breakout_strength
            + 0.10 * liquidity_quality
        )

        confidence = self._clip01(
            (
                0.35 * abs(score)
                + 0.30 * confirmation
                + 0.20 * liquidity_quality
                + 0.15 * (1.0 - conflict)
            )
            * (1.0 - 0.65 * noise_penalty)
        )

        uncertainty = self._clip01(
            0.40 * conflict
            + 0.25 * noise_penalty
            + 0.20 * (1.0 - liquidity_quality)
            + 0.15 * (1.0 - confirmation)
        )

        direction = self._direction(
            score=score,
            confidence=confidence,
        )

        veto = self._should_veto(
            market=market,
            regime=regime,
            conflict=conflict,
            confidence=confidence,
            uncertainty=uncertainty,
            patterns_by_timeframe=patterns_by_timeframe,
        )

        reasons = self._build_reasons(
            direction=direction,
            score=score,
            confidence=confidence,
            conflict=conflict,
            fake_break_strength=fake_break_strength,
            retest_strength=retest_strength,
            wick_cluster_strength=wick_cluster_strength,
            rejection_strength=rejection_strength,
            breakout_strength=breakout_strength,
            compression_strength=compression_strength,
            market=market,
            regime=regime,
            veto=veto,
        )

        evidence = {
            "score_30s": round(score_30, 6),
            "score_1m": round(score_1m, 6),
            "score_5m": round(score_5m, 6),
            "location_score": round(location_score, 6),
            "structure_score": round(structure_score, 6),
            "regime_score": round(regime_score, 6),
            "fake_break_strength": round(
                fake_break_strength, 6
            ),
            "retest_strength": round(
                retest_strength, 6
            ),
            "wick_cluster_strength": round(
                wick_cluster_strength, 6
            ),
            "rejection_strength": round(
                rejection_strength, 6
            ),
            "breakout_strength": round(
                breakout_strength, 6
            ),
            "compression_strength": round(
                compression_strength, 6
            ),
            "pattern_conflict": round(
                conflict, 6
            ),
            "liquidity_quality": round(
                liquidity_quality, 6
            ),
            "noise_penalty": round(
                noise_penalty, 6
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

    @classmethod
    def _timeframe_liquidity_score(
        cls,
        snapshot: PatternSnapshot | None,
        weight_context: float,
    ) -> float:
        if snapshot is None:
            return 0.0

        weighted = 0.0

        # Fake break / sweep is highly informative in OTC behaviour.
        weighted += cls._signal_score(
            snapshot.fake_break,
            weight=0.30,
        )

        weighted += cls._signal_score(
            snapshot.breakout_retest,
            weight=0.22,
        )

        weighted += cls._signal_score(
            snapshot.wick_cluster,
            weight=0.18,
        )

        weighted += cls._signal_score(
            snapshot.rejection,
            weight=0.15,
        )

        weighted += cls._signal_score(
            snapshot.breakout,
            weight=0.10,
        )

        weighted += cls._signal_score(
            snapshot.expansion,
            weight=0.05,
        )

        # Compression itself is neutral, but if directional evidence already
        # exists its presence increases the importance of the coming release.
        if (
            snapshot.compression is not None
            and abs(snapshot.pattern_bias) > 0.10
        ):
            weighted *= 1.0 + min(
                snapshot.compression.confidence * 0.20,
                0.20,
            )

        return cls._clip(
            weighted * weight_context,
            -weight_context,
            weight_context,
        )

    @classmethod
    def _signal_score(
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

        quality = (
            (signal.score / 100.0)
            * signal.confidence
        )

        stage_multiplier = {
            "CONFIRMED": 1.0,
            "BUILDING": 0.65,
            "FAILED": 0.0,
        }.get(signal.stage, 0.50)

        return float(
            sign
            * quality
            * stage_multiplier
            * weight
        )

    @classmethod
    def _location_context_score(
        cls,
        market: MarketIntelligenceSnapshot,
    ) -> float:
        tf = market.setup_1m
        structure = tf.structure
        technical = tf.technical

        atr = max(
            technical.atr,
            1e-12,
        )

        bullish = 0.0
        bearish = 0.0

        if structure.support_distance is not None:
            proximity = 1.0 - min(
                structure.support_distance / (atr * 1.50),
                1.0,
            )

            bullish += (
                proximity
                * max(
                    technical.lower_wick_ratio,
                    0.15,
                )
            )

        if structure.resistance_distance is not None:
            proximity = 1.0 - min(
                structure.resistance_distance / (atr * 1.50),
                1.0,
            )

            bearish += (
                proximity
                * max(
                    technical.upper_wick_ratio,
                    0.15,
                )
            )

        return cls._clip(
            bullish - bearish,
            -1.0,
            1.0,
        )

    @classmethod
    def _structure_liquidity_score(
        cls,
        market: MarketIntelligenceSnapshot,
    ) -> float:
        score = 0.0

        for timeframe, weight in (
            (market.context_5m, 0.45),
            (market.setup_1m, 0.35),
            (market.base_30s, 0.20),
        ):
            structure = timeframe.structure

            if structure.break_of_structure == "BULLISH":
                score += 0.55 * weight
            elif structure.break_of_structure == "BEARISH":
                score -= 0.55 * weight

            if structure.change_of_character == "BULLISH":
                score += 0.35 * weight
            elif structure.change_of_character == "BEARISH":
                score -= 0.35 * weight

        return cls._clip(
            score,
            -1.0,
            1.0,
        )

    @classmethod
    def _regime_score(
        cls,
        regime: RegimeSnapshot,
    ) -> float:
        if regime.primary_regime in {
            "BULLISH_EXPANSION",
            "BULLISH_TREND",
        }:
            return cls._clip01(
                regime.regime_confidence
                * max(
                    regime.trend_strength,
                    regime.expansion_strength,
                )
            )

        if regime.primary_regime in {
            "BEARISH_EXPANSION",
            "BEARISH_TREND",
        }:
            return -cls._clip01(
                regime.regime_confidence
                * max(
                    regime.trend_strength,
                    regime.expansion_strength,
                )
            )

        return cls._clip(
            regime.directional_bias * 0.30,
            -1.0,
            1.0,
        )

    @classmethod
    def _liquidity_quality(
        cls,
        p30: PatternSnapshot | None,
        p1m: PatternSnapshot | None,
        p5m: PatternSnapshot | None,
    ) -> float:
        snapshots = [
            (p30, 0.20),
            (p1m, 0.35),
            (p5m, 0.45),
        ]

        total = 0.0
        weight_total = 0.0

        for snapshot, weight in snapshots:
            if snapshot is None:
                continue

            total += (
                snapshot.pattern_quality
                * weight
            )

            weight_total += weight

        if weight_total <= 0:
            return 0.0

        return cls._clip01(
            total / weight_total
        )

    @classmethod
    def _pattern_conflict(
        cls,
        p30: PatternSnapshot | None,
        p1m: PatternSnapshot | None,
        p5m: PatternSnapshot | None,
    ) -> float:
        snapshots = [
            (p30, 0.20),
            (p1m, 0.35),
            (p5m, 0.45),
        ]

        weighted_conflict = 0.0
        total_weight = 0.0

        directional_biases: list[
            tuple[float, float]
        ] = []

        for snapshot, weight in snapshots:
            if snapshot is None:
                continue

            weighted_conflict += (
                snapshot.conflict_score
                * weight
            )
            total_weight += weight

            if abs(snapshot.pattern_bias) > 0.10:
                directional_biases.append(
                    (
                        snapshot.pattern_bias,
                        weight,
                    )
                )

        internal_conflict = (
            weighted_conflict / total_weight
            if total_weight > 0
            else 0.0
        )

        bullish = sum(
            weight * max(bias, 0.0)
            for bias, weight
            in directional_biases
        )

        bearish = sum(
            weight * max(-bias, 0.0)
            for bias, weight
            in directional_biases
        )

        directional_total = (
            bullish + bearish
        )

        if directional_total > 0:
            cross_timeframe_conflict = (
                2.0
                * min(
                    bullish,
                    bearish,
                )
                / directional_total
            )
        else:
            cross_timeframe_conflict = 0.0

        return cls._clip01(
            0.55 * internal_conflict
            + 0.45 * cross_timeframe_conflict
        )

    @classmethod
    def _pattern_strength(
        cls,
        snapshots: Mapping[int, PatternSnapshot],
        attribute: str,
    ) -> float:
        weights = {
            CONFIG.BASE_TIMEFRAME_SECONDS: 0.20,
            CONFIG.TIMEFRAME_1M_SECONDS: 0.35,
            CONFIG.TIMEFRAME_5M_SECONDS: 0.45,
        }

        total = 0.0
        weight_total = 0.0

        for timeframe, snapshot in snapshots.items():
            signal = getattr(
                snapshot,
                attribute,
                None,
            )

            if signal is None:
                continue

            weight = weights.get(
                timeframe,
                0.20,
            )

            strength = (
                (signal.score / 100.0)
                * signal.confidence
            )

            total += strength * weight
            weight_total += weight

        if weight_total <= 0:
            return 0.0

        return cls._clip01(
            total / weight_total
        )

    @staticmethod
    def _direction(
        score: float,
        confidence: float,
    ) -> str:
        if (
            confidence < CONFIG.AGENT_MIN_CONFIDENCE
            or abs(score) < 0.18
        ):
            return "WAIT"

        return (
            "BULLISH"
            if score > 0
            else "BEARISH"
        )

    @classmethod
    def _should_veto(
        cls,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        conflict: float,
        confidence: float,
        uncertainty: float,
        patterns_by_timeframe: Mapping[int, PatternSnapshot],
    ) -> bool:
        if market.readiness_state in {
            "WARMUP",
            "BLOCKED_NOISE",
        }:
            return True

        if regime.primary_regime == "HIGH_NOISE":
            return True

        if regime.noise_strength >= CONFIG.HIGH_NOISE_BLOCK_THRESHOLD:
            return True

        if conflict >= 0.75:
            return True

        if uncertainty >= 0.78:
            return True

        # Strong unresolved fake-break conflict across timeframes is dangerous.
        fake_break_directions = {
            signal.direction
            for snapshot in patterns_by_timeframe.values()
            if snapshot.fake_break is not None
            for signal in (snapshot.fake_break,)
            if signal.direction in {
                "BULLISH",
                "BEARISH",
            }
            and signal.confidence >= 0.70
        }

        if len(fake_break_directions) > 1:
            return True

        if (
            confidence < 0.30
            and market.conflict_score >= 0.50
        ):
            return True

        return False

    @staticmethod
    def _build_reasons(
        direction: str,
        score: float,
        confidence: float,
        conflict: float,
        fake_break_strength: float,
        retest_strength: float,
        wick_cluster_strength: float,
        rejection_strength: float,
        breakout_strength: float,
        compression_strength: float,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        veto: bool,
    ) -> list[str]:
        reasons: list[str] = []

        if fake_break_strength >= 0.55:
            reasons.append(
                "strong liquidity sweep / fake-break evidence"
            )

        if wick_cluster_strength >= 0.50:
            reasons.append(
                "repeated wick cluster indicates concentrated liquidity"
            )

        if rejection_strength >= 0.55:
            reasons.append(
                "rejection behaviour is materially present"
            )

        if retest_strength >= 0.55:
            reasons.append(
                "breakout retest has meaningful confirmation"
            )

        if breakout_strength >= 0.55:
            reasons.append(
                "real-breakout evidence is elevated"
            )

        if compression_strength >= 0.60:
            reasons.append(
                "compression is building before potential liquidity release"
            )

        if market.setup_1m.structure.nearest_support is not None:
            reasons.append(
                "1m support location is available for liquidity context"
            )

        if market.setup_1m.structure.nearest_resistance is not None:
            reasons.append(
                "1m resistance location is available for liquidity context"
            )

        if conflict >= 0.55:
            reasons.append(
                "liquidity evidence conflicts across timeframes"
            )

        if regime.primary_regime == "HIGH_NOISE":
            reasons.append(
                "high-noise regime reduces liquidity-read reliability"
            )

        if direction == "WAIT":
            reasons.append(
                f"liquidity evidence is not decisive "
                f"(score={score:.2f}, confidence={confidence:.2f})"
            )

        if veto:
            reasons.append(
                "liquidity agent requests a safety veto"
            )

        return reasons

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
