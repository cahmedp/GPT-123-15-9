import os
import asyncio
import json

from dotenv import load_dotenv
from BinaryOptionsToolsV2 import PocketOptionAsync


load_dotenv()


class PocketProvider:

    def __init__(self):

        self.client = None
        self.assets = []


    def build_ssid(self):

        session = os.getenv("POCKET_SESSION_ID")
        uid = os.getenv("POCKET_USER_ID")

        if not session or not uid:
            raise Exception(
                "Missing Pocket credentials"
            )

        return (
            '42["auth",'
            '{'
            f'"session":"{session}",'
            '"isDemo":1,'
            f'"uid":{uid},'
            '"platform":2,'
            '"isFastHistory":true,'
            '"isOptimized":true'
            '}'
            ']'
        )


    async def connect(self):

        print("[POCKET] Connecting...")

        self.client = PocketOptionAsync(
            self.build_ssid()
        )

        await self.client.client.connect()

        print("[POCKET] Connected")


    async def load_assets(self):

        print("[POCKET] Listening assets...")

        stream = await self.client.client.subscribe_raw()


        async for message in stream:

            text = str(message)


            if "GBPUSD" in text:

                print("\n========== ASSET DATA FOUND ==========")

                print(
                    text[:2000]
                )

                self.assets.append(text)

                break


        print(
            "[POCKET] Asset message captured"
        )


    def find_gbpusd(self):

        for asset in self.assets:

            if "GBPUSD_otc" in asset:

                return "GBPUSD_otc"

        return None



    async def close(self):

        if self.client:

            await self.client.shutdown()



async def test():

    provider = PocketProvider()

    await provider.connect()

    await provider.load_assets()


    print(
        "\nTARGET:",
        provider.find_gbpusd()
    )


    await provider.close()



if __name__ == "__main__":

    asyncio.run(test())