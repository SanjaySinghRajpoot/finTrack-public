import requests

def fetch_gmail_messages(access_token: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()
