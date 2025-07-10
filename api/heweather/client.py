import requests
import os
from config.settings import settings

BASE_URL = "https://devapi.qweather.com/v7/air/now"
CITY_ID_URL = "https://geoapi.qweather.com/v2/city/lookup"


class HeWeatherClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or settings.API_KEY

    def get_city_id(self, city_name):
        params = {"location": city_name, "key": self.api_key}
        resp = requests.get(CITY_ID_URL, params=params)
        data = resp.json()
        if data.get("code") == "200":
            return data["location"][0]["id"]
        return None

    def get_air_quality(self, city_id):
        params = {"location": city_id, "key": self.api_key}
        resp = requests.get(BASE_URL, params=params)
        return resp.json()
