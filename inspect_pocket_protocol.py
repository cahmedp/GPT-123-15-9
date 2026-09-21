import os
import asyncio
from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync


load_dotenv()


async def main():

    ssid = (
        '42["auth",'
        '{'
        f'"session":"{os.getenv("POCKET_SESSION_ID")}",'
        '"isDemo":1,'
        f'"uid":{os.getenv("POCKET_USER_ID")},'
        '"platform":2,'
        '"isFastHistory":true,'
        '"isOptimized":true'
        '}'
        ']'
    )

    client = PocketOptionAsync(ssid)

    print("CLIENT CREATED")

    print("\nRAW CLIENT:")
    print(type(client.client))

    print("\nAVAILABLE RAW METHODS:")

    for x in dir(client.client):
        if not x.startswith("_"):
            print(x)


asyncio.run(main())