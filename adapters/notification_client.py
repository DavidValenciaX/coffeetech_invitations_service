from dotenv import load_dotenv
import os
import logging
import requests

load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

NOTIFICATIONS_SERVICE_URL = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8001")

def get_notification_state_by_name(name):
    resp = requests.get(f"{NOTIFICATIONS_SERVICE_URL}/notification-states")
    resp.raise_for_status()
    for state in resp.json():
        if state["name"].lower() == name.lower():
            return state
    return None

def get_notification_type_by_name(name):
    resp = requests.get(f"{NOTIFICATIONS_SERVICE_URL}/notification-types")
    resp.raise_for_status()
    for t in resp.json():
        if t["name"].lower() == name.lower():
            return t
    return None
