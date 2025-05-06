from dotenv import load_dotenv
import os
import logging
import httpx

load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

NOTIFICATIONS_SERVICE_URL = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8001")

def get_notification_state_by_name(name):
    try:
        with httpx.Client() as client:
            resp = client.get(f"{NOTIFICATIONS_SERVICE_URL}/notification-states")
            resp.raise_for_status()
            for state in resp.json():
                if state["name"].lower() == name.lower():
                    return state
        return None
    except httpx.RequestError as exc:
        logger.error(f"Request error while getting notification state by name '{name}': {exc}")
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error while getting notification state by name '{name}': {exc.response.status_code} - {exc.response.text}")
        raise

def get_notification_type_by_name(name):
    try:
        with httpx.Client() as client:
            resp = client.get(f"{NOTIFICATIONS_SERVICE_URL}/notification-types")
            resp.raise_for_status()
            for t in resp.json():
                if t["name"].lower() == name.lower():
                    return t
        return None
    except httpx.RequestError as exc:
        logger.error(f"Request error while getting notification type by name '{name}': {exc}")
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error while getting notification type by name '{name}': {exc.response.status_code} - {exc.response.text}")
        raise

def get_user_devices_by_user_id(user_id):
    """
    Obtiene todos los dispositivos (fcm_token) asociados a un usuario.
    """
    try:
        with httpx.Client() as client:
            resp = client.get(f"{NOTIFICATIONS_SERVICE_URL}/user-devices/{user_id}")
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as exc:
        logger.error(f"Request error while getting user devices for user_id={user_id}: {exc}")
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error while getting user devices for user_id={user_id}: {exc.response.status_code} - {exc.response.text}")
        raise

def update_notification_state(notification_id, notification_state_id):
    """
    Actualiza el estado de una notificación en el microservicio de notificaciones.
    """
    try:
        with httpx.Client() as client:
            resp = client.patch(
                f"{NOTIFICATIONS_SERVICE_URL}/notifications/{notification_id}/state",
                json={"notification_state_id": notification_state_id}
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.RequestError as exc:
        logger.error(f"Request error while updating notification state for notification_id={notification_id}: {exc}")
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error while updating notification state for notification_id={notification_id}: {exc.response.status_code} - {exc.response.text}")
        raise

def get_notification_id_by_invitation_id(invitation_id):
    """
    Consulta al microservicio de notificaciones para obtener el notification_id asociado a una invitación.
    """
    # Ajusta el endpoint según tu implementación real
    try:
        with httpx.Client() as client:
            resp = client.get(f"{NOTIFICATIONS_SERVICE_URL}/notifications/by-invitation/{invitation_id}")
            print(f"Response: {resp.text}")
            # Verifica si la respuesta es exitosa
            resp.raise_for_status()
            data = resp.json()
            # Suponiendo que retorna {"notification_id": ...}
            return data.get("notification_id")
    except httpx.RequestError as exc:
        logger.error(f"Request error while getting notification_id for invitation_id={invitation_id}: {exc}")
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(f"HTTP error while getting notification_id for invitation_id={invitation_id}: {exc.response.status_code} - {exc.response.text}")
        raise

def send_notification(
    message,
    user_id,
    notification_type_id,
    entity_id,
    notification_state_id,
    fcm_token=None,
    fcm_title=None,
    fcm_body=None
):
    """
    Envía una notificación a través del servicio de notificaciones.
    """
    payload = {
        "message": message,
        "user_id": user_id,
        "notification_type_id": notification_type_id,
        "entity_id": entity_id,
        "notification_state_id": notification_state_id,
        "fcm_token": fcm_token,
        "fcm_title": fcm_title,
        "fcm_body": fcm_body
    }

    try:
        with httpx.Client() as client:
            resp = client.post(f"{NOTIFICATIONS_SERVICE_URL}/send-notification", json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise
