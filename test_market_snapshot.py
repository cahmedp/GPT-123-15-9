from intelligence.market_snapshot import SnapshotBuilder


builder = SnapshotBuilder()


features = {

    "asset": "GBPUSD_otc",

    "timeframe": 30,

    "momentum": 0.0017,

    "volatility": 0.002,

    "body_ratio": 0.5

}


state = {

    "trend": "UP",

    "momentum": "STRONG",

    "volatility": "NORMAL",

    "market_mode": "TRENDING"

}



snapshot = builder.create(

    features,

    state

)



print(snapshot)


print("\nASSET:")
print(snapshot.asset)


print("\nSTATE:")
print(snapshot.state)


print("\nFEATURES:")
print(snapshot.features)