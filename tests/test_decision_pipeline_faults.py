
"""
Decision Pipeline Fault Tests
"""

from resilience.fault_injection import (
    FaultInjector
)


def run():

    injector = FaultInjector()


    print("\n================")
    print("TRADER FAILURE")

    print(
        injector.simulate(
            "TRADER_FAILURE"
        )
    )


    print("\n================")
    print("MEMORY FAILURE")

    print(
        injector.simulate(
            "MEMORY_FAILURE"
        )
    )


    print("\n================")
    print("DATA DEGRADED")

    print(
        injector.simulate(
            "DATA_DEGRADED"
        )
    )


    print("\n================")
    print("RISK BLOCK")

    print(
        injector.simulate(
            "RISK_BLOCK"
        )
    )


if __name__ == "__main__":
    run()
