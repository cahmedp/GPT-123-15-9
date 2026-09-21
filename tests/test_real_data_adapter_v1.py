
from data.real_data_adapter_v1 import (
    CandleNormalizer,
    CandleStreamManager
)


def run():

    normalizer = CandleNormalizer()
    manager = CandleStreamManager()


    print("\n================")
    print("HEALTHY STREAM")

    candles = [
        normalizer.normalize({
            "timestamp": f"10:{i}",
            "open":100+i,
            "high":102+i,
            "low":99+i,
            "close":101+i
        })
        for i in range(3)
    ]

    print(
        manager.validate(candles)
    )


    print("\n================")
    print("DUPLICATE STREAM")

    candles.append(candles[-1])

    print(
        manager.validate(candles)
    )


if __name__ == "__main__":
    run()
