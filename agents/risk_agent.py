from __future__ import annotations

from typing import Any, Mapping, Optional

from agents.trend_agent import AgentOpinion
from config import CONFIG
from intelligence.market_intelligence import MarketIntelligenceSnapshot
from intelligence.pattern_engine import PatternSnapshot
from intelligence.regime_detector import RegimeSnapshot


class RiskAgent:
    """
    Risk-specialist member of the multi-agent reasoning system.

    Responsibilities:
    - Detect high-noise / unreliable conditions.
    - Detect timeframe and pattern conflict.
    - Detect unstable transition regimes.
    - Detect dangerous late expansion / extreme volatility.
    - Detect compression without directional confirmation.
    - Block analysis while the system is warming up.
    - Convert market risk into a safety veto when necessary.

    This agent never executes trades.
    It intentionally has a smaller directional influence than the trend,
    liquidity and pattern agents. Its main power is uncertainty + veto.
    """

    NAME = "risk_agent"

    def evaluate(
        self,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        patterns_by_timeframe: Optional[
            Mapping[int, PatternSnapshot]
        ] = None,
        session_context: Optional[
            Mapping[str, Any]
        ] = None,
    ) -> AgentOpinion:
        patterns_by_timeframe = patterns_by_timeframe or {}
        session_context = session_context or {}

        noise_risk = self._noise_risk(
            market=market,
            regime=regime,
        )

        timeframe_conflict_risk = self._clip01(
            market.conflict_score
        )

        pattern_conflict_risk = self._pattern_conflict_risk(
            patterns_by_timeframe
        )

        regime_risk = self._regime_risk(
            regime
        )

        volatility_risk = self._volatility_risk(
            market=market,
            regime=regime,
        )

        compression_risk = self._compression_risk(
            market=market,
            patterns_by_timeframe=patterns_by_timeframe,
        )

        structure_risk = self._structure_risk(
            market=market,
        )

        readiness_risk = self._readiness_risk(
            market=market,
        )

        data_risk = self._data_risk(
            session_context=session_context,
        )

        outcome_risk = self._outcome_risk(
            session_context=session_context,
        )

        risk_score = self._clip01(
            0.20 * noise_risk
            + 0.16 * timeframe_conflict_risk
            + 0.12 * pattern_conflict_risk
            + 0.12 * regime_risk
            + 0.10 * volatility_risk
            + 0.08 * compression_risk
            + 0.08 * structure_risk
            + 0.07 * readiness_risk
            + 0.04 * data_risk
            + 0.03 * outcome_risk
        )

        safety_score = self._clip01(
            1.0 - risk_score
        )

        # Risk agent has only a small directional vote. If conditions are
        # safe, it allows the existing market bias to pass through. If unsafe,
        # it collapses its directional score toward zero and can veto.
        directional_score = self._clip(
            market.multi_timeframe_bias
            * safety_score
            * 0.60,
            -1.0,
            1.0,
        )

        uncertainty = self._clip01(
            0.65 * risk_score
            + 0.20 * market.conflict_score
            + 0.15 * (
                1.0 - regime.regime_confidence
            )
        )

        confidence = self._clip01(
            (
                0.55 * safety_score
                + 0.25 * regime.regime_confidence
                + 0.20 * market.market_quality
            )
            * (1.0 - 0.45 * uncertainty)
        )

        veto = self._should_veto(
            market=market,
            regime=regime,
            risk_score=risk_score,
            noise_risk=noise_risk,
            timeframe_conflict_risk=timeframe_conflict_risk,
            pattern_conflict_risk=pattern_conflict_risk,
            volatility_risk=volatility_risk,
            readiness_risk=readiness_risk,
            data_risk=data_risk,
            outcome_risk=outcome_risk,
        )

        direction = self._direction(
            score=directional_score,
            confidence=confidence,
            veto=veto,
        )

        reasons = self._build_reasons(
            market=market,
            regime=regime,
            risk_score=risk_score,
            noise_risk=noise_risk,
            timeframe_conflict_risk=timeframe_conflict_risk,
            pattern_conflict_risk=pattern_conflict_risk,
            regime_risk=regime_risk,
            volatility_risk=volatility_risk,
            compression_risk=compression_risk,
            structure_risk=structure_risk,
            readiness_risk=readiness_risk,
            data_risk=data_risk,
            outcome_risk=outcome_risk,
            veto=veto,
        )

        evidence = {
            "risk_score": round(risk_score, 6),
            "safety_score": round(safety_score, 6),
            "noise_risk": round(noise_risk, 6),
            "timeframe_conflict_risk": round(
                timeframe_conflict_risk,
                6,
            ),
            "pattern_conflict_risk": round(
                pattern_conflict_risk,
                6,
            ),
            "regime_risk": round(regime_risk, 6),
            "volatility_risk": round(
                volatility_risk,
                6,
            ),
            "compression_risk": round(
                compression_risk,
                6,
            ),
            "structure_risk": round(
                structure_risk,
                6,
            ),
            "readiness_risk": round(
                readiness_risk,
                6,
            ),
            "data_risk": round(
                data_risk,
                6,
            ),
            "outcome_risk": round(
                outcome_risk,
                6,
            ),
            "market_quality": round(
                market.market_quality,
                6,
            ),
            "regime_confidence": round(
                regime.regime_confidence,
                6,
            ),
            "regime": regime.primary_regime,
        }

        return AgentOpinion(
            agent=self.NAME,
            direction=direction,
            score=float(directional_score),
            confidence=float(confidence),
            uncertainty=float(uncertainty),
            veto=bool(veto),
            reasons=tuple(reasons),
            evidence=evidence,
        )

    @classmethod
    def _noise_risk(
        cls,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
    ) -> float:
        return cls._clip01(
            0.55 * market.noise_score
            + 0.30 * regime.noise_strength
            + 0.15 * (
                1.0 - market.market_quality
            )
        )

    @classmethod
    def _pattern_conflict_risk(
        cls,
        patterns_by_timeframe: Mapping[
            int,
            PatternSnapshot,
        ],
    ) -> float:
        if not patterns_by_timeframe:
            return 0.0

        weights = {
            CONFIG.BASE_TIMEFRAME_SECONDS: 0.25,
            CONFIG.TIMEFRAME_1M_SECONDS: 0.35,
            CONFIG.TIMEFRAME_5M_SECONDS: 0.40,
        }

        internal = 0.0
        total_weight = 0.0

        bullish = 0.0
        bearish = 0.0

        for timeframe, snapshot in patterns_by_timeframe.items():
            weight = weights.get(
                timeframe,
                0.20,
            )

            internal += (
                snapshot.conflict_score
                * weight
            )
            total_weight += weight

            if snapshot.pattern_bias > 0:
                bullish += (
                    snapshot.pattern_bias
                    * snapshot.pattern_quality
                    * weight
                )
            elif snapshot.pattern_bias < 0:
                bearish += (
                    -snapshot.pattern_bias
                    * snapshot.pattern_quality
                    * weight
                )

        internal = (
            internal / total_weight
            if total_weight > 0
            else 0.0
        )

        directional_total = (
            bullish + bearish
        )

        cross = (
            (
                2.0
                * min(
                    bullish,
                    bearish,
                )
                / directional_total
            )
            if directional_total > 1e-12
            else 0.0
        )

        return cls._clip01(
            0.60 * internal
            + 0.40 * cross
        )

    @classmethod
    def _regime_risk(
        cls,
        regime: RegimeSnapshot,
    ) -> float:
        if regime.primary_regime == "HIGH_NOISE":
            base = 1.0
        elif regime.primary_regime == "TRANSITION":
            base = 0.80
        elif regime.primary_regime == "RANGE":
            base = 0.55
        elif regime.primary_regime == "COMPRESSION":
            base = 0.50
        else:
            base = 0.20

        confidence_penalty = (
            1.0 - regime.regime_confidence
        )

        return cls._clip01(
            0.75 * base
            + 0.25 * confidence_penalty
        )

    @classmethod
    def _volatility_risk(
        cls,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
    ) -> float:
        state_score = {
            "LOW": 0.20,
            "NORMAL": 0.10,
            "HIGH": 0.55,
            "EXTREME": 1.00,
        }.get(
            regime.volatility_state,
            0.35,
        )

        late_expansion = cls._clip01(
            max(
                market.base_30s.technical.range_vs_atr,
                market.setup_1m.technical.range_vs_atr,
            )
            / max(
                CONFIG.EXPANSION_ATR_MULTIPLIER * 2.0,
                1e-9,
            )
        )

        return cls._clip01(
            0.65 * state_score
            + 0.35 * late_expansion
        )

    @classmethod
    def _compression_risk(
        cls,
        market: MarketIntelligenceSnapshot,
        patterns_by_timeframe: Mapping[
            int,
            PatternSnapshot,
        ],
    ) -> float:
        if market.compression_pressure < 0.55:
            return 0.0

        directional_confirmation = max(
            market.directional_conviction,
            market.alignment_score,
        )

        pattern_confirmation = 0.0

        for snapshot in patterns_by_timeframe.values():
            for signal in (
                snapshot.breakout,
                snapshot.breakout_retest,
                snapshot.expansion,
            ):
                if signal is None:
                    continue

                pattern_confirmation = max(
                    pattern_confirmation,
                    (
                        signal.score / 100.0
                    ) * signal.confidence,
                )

        confirmation = max(
            directional_confirmation,
            pattern_confirmation,
        )

        return cls._clip01(
            market.compression_pressure
            * (1.0 - confirmation)
        )

    @classmethod
    def _structure_risk(
        cls,
        market: MarketIntelligenceSnapshot,
    ) -> float:
        states = (
            market.base_30s.structure.structure_state,
            market.setup_1m.structure.structure_state,
            market.context_5m.structure.structure_state,
        )

        transition_count = sum(
            1
            for state in states
            if state == "TRANSITION"
        )

        range_count = sum(
            1
            for state in states
            if state == "RANGE"
        )

        choch_count = sum(
            1
            for timeframe in (
                market.base_30s,
                market.setup_1m,
                market.context_5m,
            )
            if timeframe.structure.change_of_character
            != "NONE"
        )

        risk = (
            0.35 * (transition_count / 3.0)
            + 0.25 * (range_count / 3.0)
            + 0.40 * (choch_count / 3.0)
        )

        return cls._clip01(risk)

    @staticmethod
    def _readiness_risk(
        market: MarketIntelligenceSnapshot,
    ) -> float:
        mapping = {
            "READY": 0.05,
            "OBSERVE": 0.35,
            "WAIT_LOW_QUALITY": 0.70,
            "WAIT_CONFLICT": 0.85,
            "BLOCKED_NOISE": 1.00,
            "WARMUP": 1.00,
        }

        return float(
            mapping.get(
                market.readiness_state,
                0.60,
            )
        )

    @classmethod
    def _data_risk(
        cls,
        session_context: Mapping[str, Any],
    ) -> float:
        """
        Optional runtime health information supplied later by the orchestrator.

        Supported keys:
            data_stale: bool
            seconds_since_last_tick: float
            reconnect_count: int
            data_quality_score: float  # 0..1

        Missing information is treated neutrally so this file remains fully
        usable before the runtime coordinator is attached.
        """

        risk = 0.0

        if bool(
            session_context.get(
                "data_stale",
                False,
            )
        ):
            risk = max(
                risk,
                1.0,
            )

        seconds_since_tick = session_context.get(
            "seconds_since_last_tick"
        )

        if seconds_since_tick is not None:
            try:
                seconds_since_tick = float(
                    seconds_since_tick
                )

                risk = max(
                    risk,
                    cls._clip01(
                        seconds_since_tick
                        / max(
                            CONFIG.DATA_STALE_AFTER_SECONDS,
                            1e-9,
                        )
                    ),
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        quality = session_context.get(
            "data_quality_score"
        )

        if quality is not None:
            try:
                risk = max(
                    risk,
                    1.0
                    - cls._clip01(
                        float(quality)
                    ),
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        reconnect_count = session_context.get(
            "reconnect_count"
        )

        if reconnect_count is not None:
            try:
                reconnect_count = max(
                    int(reconnect_count),
                    0,
                )

                reconnect_risk = min(
                    reconnect_count / 10.0,
                    0.60,
                )

                risk = max(
                    risk,
                    reconnect_risk,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        return cls._clip01(risk)

    @classmethod
    def _outcome_risk(
        cls,
        session_context: Mapping[str, Any],
    ) -> float:
        """
        Optional defensive-mode information supplied later by the journal /
        learning system.

        Supported keys:
            consecutive_bad_outcomes: int
            defensive_mode: bool
        """

        if bool(
            session_context.get(
                "defensive_mode",
                False,
            )
        ):
            return 1.0

        count = session_context.get(
            "consecutive_bad_outcomes",
            0,
        )

        try:
            count = max(
                int(count),
                0,
            )
        except (
            TypeError,
            ValueError,
        ):
            count = 0

        if CONFIG.MAX_CONSECUTIVE_BAD_OUTCOMES <= 0:
            return 0.0

        return cls._clip01(
            count
            / CONFIG.MAX_CONSECUTIVE_BAD_OUTCOMES
        )

    @classmethod
    def _should_veto(
        cls,
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        risk_score: float,
        noise_risk: float,
        timeframe_conflict_risk: float,
        pattern_conflict_risk: float,
        volatility_risk: float,
        readiness_risk: float,
        data_risk: float,
        outcome_risk: float,
    ) -> bool:
        if market.readiness_state in {
            "WARMUP",
            "BLOCKED_NOISE",
        }:
            return True

        if regime.primary_regime == "HIGH_NOISE":
            return True

        if (
            noise_risk
            >= CONFIG.HIGH_NOISE_BLOCK_THRESHOLD
        ):
            return True

        if timeframe_conflict_risk >= 0.90:
            return True

        if pattern_conflict_risk >= 0.90:
            return True

        if volatility_risk >= 0.90:
            return True

        if readiness_risk >= 0.90:
            return True

        if data_risk >= 0.75:
            return True

        if outcome_risk >= 1.0:
            return True

        if (
            risk_score
            > CONFIG.MAX_ACCEPTABLE_RISK_SCORE
        ):
            return True

        return False

    @staticmethod
    def _direction(
        score: float,
        confidence: float,
        veto: bool,
    ) -> str:
        if veto:
            return "WAIT"

        if (
            confidence < CONFIG.AGENT_MIN_CONFIDENCE
            or abs(score) < 0.12
        ):
            return "WAIT"

        return (
            "BULLISH"
            if score > 0
            else "BEARISH"
        )

    @staticmethod
    def _build_reasons(
        market: MarketIntelligenceSnapshot,
        regime: RegimeSnapshot,
        risk_score: float,
        noise_risk: float,
        timeframe_conflict_risk: float,
        pattern_conflict_risk: float,
        regime_risk: float,
        volatility_risk: float,
        compression_risk: float,
        structure_risk: float,
        readiness_risk: float,
        data_risk: float,
        outcome_risk: float,
        veto: bool,
    ) -> list[str]:
        reasons: list[str] = []

        if noise_risk >= 0.60:
            reasons.append(
                "market noise is elevated"
            )

        if timeframe_conflict_risk >= 0.50:
            reasons.append(
                "timeframes materially disagree"
            )

        if pattern_conflict_risk >= 0.50:
            reasons.append(
                "pattern evidence is conflicting"
            )

        if regime_risk >= 0.60:
            reasons.append(
                f"regime is structurally risky: "
                f"{regime.primary_regime.lower()}"
            )

        if volatility_risk >= 0.60:
            reasons.append(
                "volatility/late-expansion risk is elevated"
            )

        if compression_risk >= 0.55:
            reasons.append(
                "compression lacks sufficient confirmation"
            )

        if structure_risk >= 0.55:
            reasons.append(
                "market structure is unstable"
            )

        if readiness_risk >= 0.70:
            reasons.append(
                f"market readiness is unsafe: "
                f"{market.readiness_state.lower()}"
            )

        if data_risk >= 0.50:
            reasons.append(
                "live-data reliability requires caution"
            )

        if outcome_risk >= 0.50:
            reasons.append(
                "recent outcomes require defensive behaviour"
            )

        if risk_score <= 0.30:
            reasons.append(
                "overall market risk is low"
            )
        elif risk_score <= CONFIG.MAX_ACCEPTABLE_RISK_SCORE:
            reasons.append(
                "overall market risk is moderate"
            )
        else:
            reasons.append(
                "overall market risk exceeds allowed threshold"
            )

        if veto:
            reasons.append(
                "risk agent requests a safety veto"
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
