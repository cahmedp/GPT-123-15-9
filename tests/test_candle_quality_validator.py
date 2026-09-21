
from validation.candle_quality_validator import CandleQualityValidator


def run():

    validator = CandleQualityValidator()

    print("\n================")
    print("CLEAN EXPANSION")

    candles = []

    for i in range(10):
        candles.append({
            "open":100+i,
            "close":101+i,
            "high":102+i,
            "low":99+i
        })

    print(
        validator.validate(candles)
    )


    print("\n================")
    print("NOISY MARKET")

    candles = []

    for i in range(10):
        candles.append({
            "open":100,
            "close":100.1,
            "high":105,
            "low":95
        })

    print(
        validator.validate(candles)
    )


if __name__ == "__main__":
    run()
