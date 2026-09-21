import asyncio

from data.pocket_provider import PocketProvider
from data.asset_manager import AssetManager
from data.tick_stream import TickStream
from data.tick_adapter import TickAdapter

from intelligence.feature_engine import FeatureEngine
from intelligence.market_state import MarketState
from intelligence.market_snapshot import MarketSnapshot
from intelligence.market_intelligence import MarketIntelligence

from intelligence.regime_detector import RegimeDetector

from agents.trend_agent import TrendAgent


async def main():

    symbol = "GBPUSD_otc"

    print("START")

    provider = PocketProvider()
    await provider.connect()

    print("POCKET READY")


    # هنا نستخدم البنية الموجودة
    # نحتاج أول Snapshot حقيقي من النظام


if __name__ == "__main__":
    asyncio.run(main())