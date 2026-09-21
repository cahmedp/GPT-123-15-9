from data.tick_adapter import TickAdapter


raw_tick = {

    "symbol": "GBPUSD_otc",

    "raw": {

        "timestamp": 1789507856,

        "close": "1.3336"

    }

}


print("Creating MarketTick...")


tick = TickAdapter.convert(
    raw_tick
)


print("\nTYPE:")
print(type(tick))


print("\nOBJECT:")
print(tick)


print("\nFIELDS:")
print("asset =", tick.asset)
print("price =", tick.price)
print("timestamp =", tick.timestamp)
print("received_at =", tick.received_at)