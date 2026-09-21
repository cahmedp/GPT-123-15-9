
from learning.market_health_memory import MarketHealthMemory


def run():

    memory = MarketHealthMemory()

    print("\n================")
    print("LOSS AVOIDED")
    print(memory.evaluate(
        "DEFENSIVE",
        "NO_TRADE",
        "LOSS_AVOIDED"
    ))

    print("\n================")
    print("TOO STRICT")
    print(memory.evaluate(
        "DEFENSIVE",
        "NO_TRADE",
        "WOULD_HAVE_WIN"
    ))

    print("\n================")
    print("CAUTIOUS")
    print(memory.evaluate(
        "CAUTIOUS",
        "TRADE",
        "MATCH"
    ))


if __name__ == "__main__":
    run()
