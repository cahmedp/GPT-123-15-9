from data.asset_manager import AssetManager


manager = AssetManager()


raw = [

    [
        86,
        "GBPUSD_otc",
        "GBP/USD OTC",
        "currency"
    ],

    [
        10,
        "EURUSD_otc",
        "EUR/USD OTC",
        "currency"
    ]

]


manager.load_from_raw(raw)


print(
    "TOTAL:",
    manager.count()
)


print(
    "\nGBPUSD:"
)

print(
    manager.get_asset(
        "GBPUSD_otc"
    )
)


print(
    "\nSEARCH USD:"
)

print(
    manager.search(
        "USD"
    )
)