from adapters.notification_client import send_notification as send_notification_service
import pytz
import logging

bogota_tz = pytz.timezone("America/Bogota")
logger = logging.getLogger(__name__)

def send_notification(
    message,
    user_id,
    notification_type_id,
    entity_type,
    entity_id,
    notification_state_id,
    fcm_token=None,
    fcm_title=None,
    fcm_body=None
):
    try:
        response = send_notification_service(
            message=message,
            user_id=user_id,
            notification_type_id=notification_type_id,
            entity_type=entity_type,
            entity_id=entity_id,
            notification_state_id=notification_state_id,
            fcm_token=fcm_token,
            fcm_title=fcm_title,
            fcm_body=fcm_body
        )
        return response
    except Exception as e:
        logger.error(f"Error enviando notificación: {str(e)}")
        raise
