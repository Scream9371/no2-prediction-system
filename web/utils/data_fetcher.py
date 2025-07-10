import requests


def fetch_no2_data(city_id):
    resp = requests.get(f"/api/no2/{city_id}")
    if resp.status_code == 200:
        return resp.json()
    return []
