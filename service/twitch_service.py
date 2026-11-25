import requests

TOKEN_URL = "http://localhost:8080/auth/token"
USERS_URL = "http://localhost:8080/mock/users"


def _get_token(client_id: str, client_secret: str) -> str:
    response = requests.post(
        TOKEN_URL,
        params={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_twitch_data_specific_try(login: str, client_id: str, client_secret: str):
    try:
        token = _get_token(client_id, client_secret)
        headers = {
            "Client-Id": client_id,
            "Authorization": f"Bearer {token}",
        }
        response = requests.get(USERS_URL, headers=headers, params={"login": login}, timeout=15)
        if response.status_code != 200:
            return {"error": "Streamer not found"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

    data = response.json().get("data", [])
    if not data:
        return {"error": "Streamer not found"}

    streamer = data[0]
    result = {
        "id": streamer.get("id"),
        "login": streamer.get("login"),
        "display_name": streamer.get("display_name"),
        "description": streamer.get("description"),
    }
    return result