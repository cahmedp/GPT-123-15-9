from typing import Dict, List, Optional


class AssetManager:
    """
    مسؤول عن:
    - تحويل بيانات الأصول الخام إلى بيانات منظمة
    - البحث عن الأصول
    - توفير معلومات الأصل للباقي من النظام
    """

    def __init__(self):

        self.assets: Dict[str, dict] = {}


    def load_from_raw(self, raw_assets: list):

        """
        استقبال بيانات الأصول الخام من Pocket Option

        مثال:
        [
          id,
          symbol,
          name,
          type,
          ...
        ]
        """

        self.assets.clear()


        for item in raw_assets:

            if not isinstance(item, list):
                continue


            if len(item) < 3:
                continue


            asset_id = item[0]
            symbol = item[1]
            name = item[2]


            asset = {

                "id": asset_id,

                "symbol": symbol,

                "name": name,

                "raw": item

            }


            self.assets[symbol] = asset



    def get_asset(
        self,
        symbol: str
    ) -> Optional[dict]:

        return self.assets.get(symbol)



    def search(
        self,
        keyword: str
    ) -> List[dict]:

        result = []


        keyword = keyword.lower()


        for asset in self.assets.values():

            if (
                keyword in asset["symbol"].lower()
                or
                keyword in asset["name"].lower()
            ):

                result.append(asset)


        return result



    def count(self):

        return len(self.assets)



    def all_assets(self):

        return list(
            self.assets.values()
        )