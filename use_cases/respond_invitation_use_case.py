from utils.response import create_response
from models.models import Invitations
from sqlalchemy.orm import Session
# Adapters para microservicios
from adapters.farm_client import get_farm_by_id, create_user_role_farm, get_user_role_farm_state_by_name
from adapters.user_client import get_role_name_by_id, create_user_role
from adapters.notification_client import (
    get_notification_state_by_name,
    get_notification_type_by_name,
    send_notification,
    delete_notifications_by_invitation_id
)
import pytz
import logging

from utils.constants import (
    STATE_ACTIVE,
    NOTIFICATION_STATE_RESPONDED,
    NOTIFICATION_TYPE_ACCEPTED,
    NOTIFICATION_TYPE_REJECTED
)

logger = logging.getLogger(__name__)

bogota_tz = pytz.timezone("America/Bogota")


def _validate_invitation(invitation_id: int, user, db: Session):
    """Validate invitation exists and user has permission to respond."""
    invitation = db.query(Invitations).filter(Invitations.invitation_id == invitation_id).first()
    if not invitation:
        return None, create_response("error", "Invitación no encontrada", status_code=404)
    
    if user.user_id != invitation.invited_user_id:
        return None, create_response("error", "No tienes permiso para responder esta invitación", status_code=403)
    
    return invitation, None


def _delete_invitation_notifications(invitation_id: int):
    """Delete all invitation-related notifications."""
    try:
        delete_response = delete_notifications_by_invitation_id(invitation_id)
        if delete_response and delete_response.get("deleted_count", 0) > 0:
            logger.info(f"Notificaciones de invitación eliminadas para la invitación {invitation_id}.")
        else:
            logger.info(f"No se encontraron notificaciones de invitación para la invitación {invitation_id}.")
    except Exception as e:
        logger.error(f"Error eliminando notificaciones de invitación para la invitación {invitation_id}: {str(e)}")


def _create_user_role_farm_association(user_id: int, suggested_role_id: int, farm_id: int):
    """Create user-role-farm association."""
    suggested_role_name = get_role_name_by_id(suggested_role_id)
    if not suggested_role_name:
        return create_response("error", "El rol sugerido no es válido", status_code=400)
    
    try:
        # Create user_role
        user_role_response = create_user_role(user_id, suggested_role_name)
        user_role_id = user_role_response.get("user_role_id")
        if not user_role_id:
            return create_response("error", "No se pudo obtener el user_role_id", status_code=500)

        # Get active state for UserRoleFarm
        urf_active_state = get_user_role_farm_state_by_name(STATE_ACTIVE)
        if not urf_active_state or not urf_active_state.get("user_role_farm_state_id"):
            return create_response("error", "No se pudo obtener el estado 'Activo' para UserRoleFarm", status_code=500)
        
        urf_active_state_id = urf_active_state["user_role_farm_state_id"]

        # Create UserRoleFarm association
        urf_response = create_user_role_farm(user_role_id, farm_id, urf_active_state_id)
        if not urf_response or urf_response.get("status") != "success":
            return create_response("error", f"No se pudo asociar el usuario a la finca: {urf_response}", status_code=500)
        
        return None
    except Exception as e:
        return create_response("error", f"No se pudo asociar el usuario a la finca: {str(e)}", status_code=500)


def _send_response_notification(user_name: str, farm_id: int, inviter_user_id: int, invitation_id: int, 
                               notification_type_name: str, action_verb: str):
    """Send notification to inviter about invitation response."""
    notification_type = get_notification_type_by_name(notification_type_name)
    responded_state = get_notification_state_by_name(NOTIFICATION_STATE_RESPONDED)
    
    farm = get_farm_by_id(farm_id)
    if farm is None:
        return create_response("error", "Finca no encontrada", status_code=404)
    
    notification_message = f"El usuario {user_name} ha {action_verb} tu invitación a la finca {farm.name}."
    
    send_notification(
        message=notification_message,
        user_id=inviter_user_id,
        notification_type_id=notification_type["notification_type_id"] if notification_type else None,
        invitation_id=invitation_id,
        notification_state_id=responded_state["notification_state_id"] if responded_state else None,
        fcm_title=f"Invitación {action_verb}",
        fcm_body=notification_message,
    )
    return None


def respond_invitation(invitation_id: int, action: str, user, db: Session):
    # Validate invitation and permissions
    invitation, error_response = _validate_invitation(invitation_id, user, db)
    if error_response:
        return error_response

    # Save invitation data for notifications
    farm_id = invitation.farm_id
    inviter_user_id = invitation.inviter_user_id
    suggested_role_id = invitation.suggested_role_id

    # Delete invitation notifications
    _delete_invitation_notifications(invitation_id)

    # Handle accept action
    if action.lower() == "accept":
        # Create user-role-farm association
        association_error = _create_user_role_farm_association(user.user_id, suggested_role_id, farm_id)
        if association_error:
            return association_error

        # Delete invitation and notify
        db.delete(invitation)
        db.commit()
        logger.info(f"Invitación {invitation_id} eliminada después de ser aceptada")

        notification_error = _send_response_notification(
            user.name, farm_id, inviter_user_id, invitation_id, 
            NOTIFICATION_TYPE_ACCEPTED, "aceptado"
        )
        if notification_error:
            return notification_error

        return create_response("success", "Has aceptado la invitación exitosamente", status_code=200)

    # Handle reject action
    elif action.lower() == "reject":
        # Delete invitation and notify
        db.delete(invitation)
        db.commit()
        logger.info(f"Invitación {invitation_id} eliminada después de ser rechazada")

        notification_error = _send_response_notification(
            user.name, farm_id, inviter_user_id, invitation_id, 
            NOTIFICATION_TYPE_REJECTED, "rechazado"
        )
        if notification_error:
            return notification_error

        return create_response("success", "Has rechazado la invitación exitosamente", status_code=200)

    else:
        return create_response("error", "Acción inválida. Debes usar 'accept' o 'reject'", status_code=400)
