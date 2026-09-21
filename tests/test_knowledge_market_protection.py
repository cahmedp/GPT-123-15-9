
from learning.knowledge_promotion_gate import KnowledgePromotionGate
from risk.market_health_guard import MarketHealthGuard


def run():

    print("\n================")
    print("PROMOTION")


    gate = KnowledgePromotionGate()

    print(
        gate.evaluate(
            "ACTIVE",
            "STRONG_EVIDENCE",
            "STABLE",
            100
        )
    )


    print("\n================")
    print("STERILE MARKET")


    guard = MarketHealthGuard()

    print(
        guard.evaluate(
            volatility=0.10,
            structure_quality=0.30,
            noise_score=0.90
        )
    )


    print("\n================")
    print("CAUTIOUS MARKET")


    print(
        guard.evaluate(
            volatility=0.25,
            structure_quality=0.45,
            noise_score=0.75
        )
    )


if __name__ == "__main__":
    run()
