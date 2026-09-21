
"""
Data Quality Gate Test
"""

from datetime import datetime

from intelligence.data_quality_gate import (
    DataQualityGate
)


def run():

    gate = DataQualityGate()


    print("\n================")
    print("VALID CANDLE")


    now = datetime.utcnow().timestamp()

    result = gate.validate(
        {
            "candle_id":"NZDCAD_021230",
            "timestamp":now,
            "closed":True
        }
    )

    print(result)


    print("\n================")
    print("DUPLICATE CANDLE")


    result = gate.validate(
        {
            "candle_id":"NZDCAD_021230",
            "timestamp":now+1,
            "closed":True
        }
    )

    print(result)


    print("\n================")
    print("OPEN CANDLE")


    result = gate.validate(
        {
            "candle_id":"NZDCAD_021300",
            "timestamp":now+30,
            "closed":False
        }
    )

    print(result)


if __name__ == "__main__":
    run()
