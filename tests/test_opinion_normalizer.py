
from agents.opinion_normalizer import OpinionNormalizer


def run():

    n = OpinionNormalizer()

    print("\n================")
    print("SAME MEANING")

    print(
        n.normalize(
            "STRUCTURE_TRADER",
            "FOLLOW_STRUCTURE"
        )
    )


    print(
        n.normalize(
            "LIQUIDITY_TRADER",
            "CLEAR"
        )
    )


if __name__ == "__main__":
    run()
