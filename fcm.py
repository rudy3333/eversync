import json
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from django.conf import settings
import requests

def send_push_notification(token, title, body, data=None):
    creds = service_account.Credentials.from_service_account_file(
        settings.FCM_SERVICE_ACCOUNT,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )

    creds.refresh(Request()) 

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json; UTF-8",
    }

    url = f"https://fcm.googleapis.com/v1/projects/{creds.project_id}/messages:send"

    message = {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": data or {}
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(message))
    return response.json()