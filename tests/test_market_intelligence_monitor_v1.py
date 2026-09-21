
from monitor.market_intelligence_monitor_v1 import (
    MarketIntelligenceMonitor
)


def run():

    monitor = MarketIntelligenceMonitor()

    print("\n================")
    print("FRAME MONITOR")

    for item in monitor.frames():
        print(item)


    print("\n================")
    print("INDICATOR HEALTH")

    for item in monitor.indicators():
        print(item)


    print("\n================")
    print("SYSTEM")

    print(
        monitor.health_report()["system"]
    )


if __name__ == "__main__":
    run()
