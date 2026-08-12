import hmac
import os

API_KEY = os.environ["API_KEY"]


def lambda_handler(event, context):
    headers = event.get("headers") or {}
    provided_key = headers.get("x-api-key") or headers.get("X-Api-Key") or ""
    is_authorized = hmac.compare_digest(provided_key, API_KEY)
    return {"isAuthorized": is_authorized}
