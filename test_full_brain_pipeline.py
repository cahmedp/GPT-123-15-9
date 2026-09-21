import asyncio
import time

from data.pocket_provider import PocketProvider
from data.tick_stream import TickStream
from data.candle_builder import CandleBuilder

from intelligence.market_intelligence import MarketIntelligenceEngine
from intelligence.regime_detector import RegimeDetector
from intelligence.pattern_engine import PatternEngine

from agents.trend_agent import TrendAgent
from agents.pattern_agent import PatternAgent
from agents.liquidity_agent import LiquidityAgent
from agents.risk_agent import RiskAgent
from agents.analyst_coordinator import AnalystCoordinator


ASSET = "GBPUSD_otc"


async def main():

    print("=" * 70)
    print("FULL BRAIN PIPELINE TEST")
    print("=" * 70)


    # =========================
    # CONNECT
    # =========================

    provider = PocketProvider()

    await provider.connect()

    print("[OK] Pocket connected")


    client = provider.client

    print("[OK] Client ready")


    # =========================
    # CANDLE BUILDER
    # =========================

    candle_builder = CandleBuilder(
        timeframes=[30, 60, 300]
    )


    # =========================
    # STREAM
    # =========================

    stream = TickStream(
        client,
        ASSET
    )


    candles_by_tf = {
        30: [],
        60: [],
        300: []
    }


    print("[WAIT] Collecting candles...")


    async for tick in stream.stream():

        result = candle_builder.add_tick(tick)


        for tf, candles in result.items():

            if candles:
                candles_by_tf[tf].extend(candles)


        ready = all(
            len(candles_by_tf[tf]) >= 30
            for tf in [30, 60, 300]
        )


        if ready:
            break



    print("[OK] Candles ready")

    for tf in candles_by_tf:
        print(
            tf,
            "seconds:",
            len(candles_by_tf[tf])
        )


    # =========================
    # MARKET INTELLIGENCE
    # =========================

    intelligence = MarketIntelligenceEngine()


    market = intelligence.analyze(
        candles_by_tf
    )


    print("\n===== MARKET =====")
    print(market)


    # =========================
    # PATTERNS
    # =========================

    pattern_engine = PatternEngine()


    patterns = {}


    for tf in [30, 60, 300]:

        candles = candles_by_tf[tf]

        technical_engine = intelligence.feature_engine
        structure_engine = intelligence.structure_engine


        technical = technical_engine.calculate(
            candles
        )


        structure = structure_engine.analyze(
            candles,
            technical
        )


        patterns[tf] = pattern_engine.analyze(
            candles,
            technical,
            structure
        )


    print("\n===== PATTERNS READY =====")


    # =========================
    # REGIME
    # =========================

    regime_detector = RegimeDetector()


    regime = regime_detector.detect(
        market,
        patterns
    )


    print("\n===== REGIME =====")
    print(regime)



    # =========================
    # AGENTS
    # =========================

    coordinator = AnalystCoordinator(

        trend_agent=TrendAgent(),

        pattern_agent=PatternAgent(),

        liquidity_agent=LiquidityAgent(),

        risk_agent=RiskAgent(),

    )


    debate = coordinator.evaluate(

        market,

        regime,

        patterns

    )


    print("\n===== FINAL DEBATE =====")
    print(debate)



    await provider.close()



if __name__ == "__main__":
    asyncio.run(main())