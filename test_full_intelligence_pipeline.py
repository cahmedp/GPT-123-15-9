import time

from data.pocket_connector import HistoricalCandle

from features.technical_features import TechnicalFeatureEngine
from features.market_structure import MarketStructureEngine

from intelligence.pattern_engine import PatternEngine
from intelligence.market_intelligence import MarketIntelligenceEngine
from intelligence.regime_detector import RegimeDetector

from agents.trend_agent import TrendAgent
from agents.analyst_coordinator import AnalystCoordinator


def build_candles():

    candles = []

    price = 1.3330

    for i in range(60):

        candle = HistoricalCandle(

            timestamp=time.time() + i * 30,

            open=price,

            high=price + 0.0005,

            low=price - 0.0002,

            close=price + 0.0003,

            asset="GBPUSD_otc",

            timeframe_seconds=30

        )

        candles.append(candle)

        price += 0.0001


    return candles



def main():

    print("=" * 60)
    print("FULL INTELLIGENCE PIPELINE TEST")
    print("=" * 60)



    candles = build_candles()


    print("\nCandles created:", len(candles))


    # Feature layer

    technical_engine = TechnicalFeatureEngine()

    structure_engine = MarketStructureEngine()



    technical = technical_engine.analyze(
        candles
    )


    structure = structure_engine.analyze(
        candles
    )


    print("\nTECHNICAL:")
    print(technical)



    print("\nSTRUCTURE:")
    print(structure)



    # Pattern

    pattern_engine = PatternEngine()


    pattern = pattern_engine.analyze(

        candles,

        technical,

        structure

    )


    print("\nPATTERN:")
    print(pattern)



    # Market Intelligence

    intelligence_engine = MarketIntelligenceEngine(

        technical_engine,

        structure_engine

    )


    market = intelligence_engine.analyze(

        {
            30: candles,
            60: candles,
            300: candles
        }

    )


    print("\nMARKET INTELLIGENCE:")
    print(market)



    # Regime

    regime_detector = RegimeDetector()


    regime = regime_detector.detect(

        market,

        {
            30: pattern,
            60: pattern,
            300: pattern
        }

    )


    print("\nREGIME:")
    print(regime)



    # Agent

    trend_agent = TrendAgent()


    opinion = trend_agent.evaluate(

        market,

        regime

    )


    print("\nTREND AGENT:")
    print(opinion)



    # Coordinator

    coordinator = AnalystCoordinator(

        trend_agent=trend_agent

    )


    debate = coordinator.evaluate(

        market,

        regime,

        {
            30: pattern,
            60: pattern,
            300: pattern
        }

    )


    print("\nFINAL DEBATE:")
    print(debate)



if __name__ == "__main__":

    main()