from datetime import datetime
import pytz
import logging

# Importa tus modelos y función FCM aquí
from models.models import Notifications
from utils.fcm import send_fcm_notification

bogota_tz = pytz.timezone("America/Bogota")
logger = logging.getLogger(__name__)

def send_notification(
    db,
    message,
    user_id,
    notification_type_id,
    invitation_id,
    farm_id,
    notification_state_id,
    fcm_token=None,
    fcm_title=None,
    fcm_body=None
):
    try:
        new_notification = Notifications(
            message=message,
            date=datetime.now(bogota_tz),
            user_id=user_id,
            notification_type_id=notification_type_id,
            invitation_id=invitation_id,
            farm_id=farm_id,
            notification_state_id=notification_state_id
        )
        db.add(new_notification)
        db.commit()
        # Enviar notificación FCM si hay token y mensaje
        if fcm_token and fcm_title and fcm_body:
            send_fcm_notification(fcm_token, fcm_title, fcm_body)
    except Exception as e:
        db.rollback()
        logger.error(f"Error enviando notificación: {str(e)}")
