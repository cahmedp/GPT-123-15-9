
from storage.sqlite_storage_v1 import (
    SQLiteDatabase,
    FeedbackRepository
)


def run():

    print("\n================")
    print("DATABASE INIT")

    db = SQLiteDatabase(
        ":memory:"
    )

    print("TABLES CREATED")


    print("\n================")
    print("SAVE FEEDBACK")

    repo = FeedbackRepository(db)

    repo.save(
        "BULLISH_EXPANSION",
        "CALL",
        "CALL",
        "MATCH",
        1
    )

    print(
        "FEEDBACK_SAVED"
    )


if __name__ == "__main__":
    run()
