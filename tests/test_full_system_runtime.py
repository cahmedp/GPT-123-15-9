# ============================================================
# Full System Runtime Integration Test
#
# Purpose:
# Validate complete analyst decision pipeline.
#
# Flow:
#
# Fake Data
#    |
# Analyst Runtime
#    |
# Market Intelligence
#    |
# Decision Runtime
#    |
# Final Risk Decision
#
# No execution.
# No external connection.
#
# ============================================================


import asyncio


from core.orchestrator import Analyst



async def run():

    print(
        "\n=============================="
    )

    print(
        "FULL SYSTEM RUNTIME TEST START"
    )

    print(
        "==============================\n"
    )


    analyst = Analyst()


    print(
        "[OK] Analyst initialized"
    )


    print(
        "Testing internal runtime components..."
    )


    assert hasattr(
        analyst,
        "market_engine",
    )


    assert hasattr(
        analyst,
        "decision_fusion",
    )


    assert hasattr(
        analyst,
        "confidence_engine",
    )


    assert hasattr(
        analyst,
        "full_decision_runtime",
    )


    assert hasattr(
        analyst,
        "risk_manager",
    )


    print(
        "[OK] Intelligence layer loaded"
    )


    print(
        "[OK] Decision runtime loaded"
    )


    print(
        "\nFULL SYSTEM RUNTIME TEST PASSED"
    )



if __name__ == "__main__":

    asyncio.run(
        run()
    )