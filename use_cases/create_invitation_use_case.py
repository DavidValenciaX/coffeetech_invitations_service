from sqlalchemy.orm import Session
from utils.response import create_response
from datetime import datetime
from adapters.farm_client import get_farm_by_id, get_user_role_farm, get_user_role_farm_state_by_name
from adapters.user_client import get_role_name_by_id, get_role_permissions_for_user_role, user_verification_by_email
from adapters.notification_client import get_notification_state_by_name, get_notification_type_by_name, send_notification, delete_notifications_by_invitation_id
from models.models import Invitations
import pytz
import logging

from utils.constants import (
    ROLE_ADMIN_FARM,
    ROLE_OPERATOR_FARM,
    STATE_ACTIVE,
    NOTIFICATION_TYPE_INVITATION,
    NOTIFICATION_STATE_PENDING
)

bogota_tz = pytz.timezone("America/Bogota")

logger = logging.getLogger(__name__)

def _validate_farm_and_user_access(invitation_data, user):
    """Validate farm exists and user has access to it."""
    farm = get_farm_by_id(invitation_data.farm_id)
    if farm is None:
        return None, create_response("error", "Finca no encontrada", status_code=404)

    urf_active_state = get_user_role_farm_state_by_name(STATE_ACTIVE)
    if not urf_active_state or not urf_active_state.get("user_role_farm_state_id"):
        return None, create_response("error", "No se pudo obtener el estado 'Activo' para UserRoleFarm", status_code=500)
    
    urf_active_state_id = urf_active_state["user_role_farm_state_id"]
    urf = get_user_role_farm(user.user_id, invitation_data.farm_id)
    if not urf or getattr(urf, "user_role_farm_state_id", None) != urf_active_state_id:
        return None, create_response("error", "No tienes acceso a esta finca", status_code=403)

    return {"farm": farm, "urf": urf, "urf_active_state_id": urf_active_state_id}, None

def _validate_role_permissions(invitation_data, urf):
    """Validate suggested role and user permissions."""
    suggested_role_name = get_role_name_by_id(invitation_data.suggested_role_id)
    if not suggested_role_name:
        return None, create_response("error", "El rol sugerido no es válido", status_code=400)

    inviter_permissions = get_role_permissions_for_user_role(urf.user_role_id)
    
    if suggested_role_name == ROLE_ADMIN_FARM and "add_administrator_farm" not in inviter_permissions:
        return None, create_response("error", "No tienes permiso para invitar a un Administrador de Finca", status_code=403)
    elif suggested_role_name == ROLE_OPERATOR_FARM and "add_operator_farm" not in inviter_permissions:
        return None, create_response("error", "No tienes permiso para invitar a un Operador de Campo", status_code=403)
    elif suggested_role_name not in [ROLE_ADMIN_FARM, ROLE_OPERATOR_FARM]:
        return None, create_response("error", f"No puedes invitar a colaboradores de rol {suggested_role_name} ", status_code=403)

    return suggested_role_name, None

def _validate_invited_user(invitation_data, urf_active_state_id):
    """Validate invited user exists and is not already associated with the farm."""
    invited_user = user_verification_by_email(invitation_data.email)
    if not invited_user:
        return None, create_response("error", "El usuario no está registrado", status_code=404)

    urf_invited = get_user_role_farm(invited_user.user_id, invitation_data.farm_id)
    if urf_invited and getattr(urf_invited, "user_role_farm_state_id", None) == urf_active_state_id:
        return None, create_response("error", "El usuario ya está asociado a la finca con un estado activo", status_code=400)

    return invited_user, None

def _handle_invitation_creation_or_update(invitation_data, user, invited_user, db):
    """Create new invitation or update existing one."""
    existing_invitation = db.query(Invitations).filter(
        Invitations.invited_user_id == invited_user.user_id,
        Invitations.farm_id == invitation_data.farm_id
    ).first()

    if existing_invitation:
        existing_invitation.invitation_date = datetime.now(bogota_tz)
        existing_invitation.suggested_role_id = invitation_data.suggested_role_id
        existing_invitation.inviter_user_id = user.user_id
        db.commit()
        db.refresh(existing_invitation)
        logger.info(f"Invitación existente actualizada: {existing_invitation.invitation_id}")
        
        try:
            delete_notifications_by_invitation_id(existing_invitation.invitation_id)
            logger.info(f"Notificaciones de invitación anteriores eliminadas para la invitación actualizada {existing_invitation.invitation_id}")
        except Exception as e:
            logger.error(f"Error eliminando notificaciones anteriores para la invitación {existing_invitation.invitation_id}: {str(e)}")
        
        return existing_invitation
    else:
        new_invitation = Invitations(
            invited_user_id=invited_user.user_id,
            suggested_role_id=invitation_data.suggested_role_id,
            farm_id=invitation_data.farm_id,
            inviter_user_id=user.user_id,
            invitation_date=datetime.now(bogota_tz)
        )
        db.add(new_invitation)
        db.commit()
        db.refresh(new_invitation)
        logger.info(f"Nueva invitación creada: {new_invitation.invitation_id}")
        return new_invitation

def _send_invitation_notification(invitation, invited_user, suggested_role_name, farm):
    """Send notification to invited user."""
    notification_pending_state = get_notification_state_by_name(NOTIFICATION_STATE_PENDING)
    if not notification_pending_state:
        logger.error(f"El estado '{NOTIFICATION_STATE_PENDING}' no fue encontrado para 'Notifications'")
        return create_response("error", f"El estado '{NOTIFICATION_STATE_PENDING}' no fue encontrado para 'Notifications'", status_code=400)

    invitation_notification_type = get_notification_type_by_name(NOTIFICATION_TYPE_INVITATION)
    if not invitation_notification_type:
        logger.error(f"No se encontró el tipo de notificación '{NOTIFICATION_TYPE_INVITATION}'")
        return create_response("error", f"No se encontró el tipo de notificación '{NOTIFICATION_TYPE_INVITATION}'", status_code=400)

    send_notification(
        message=f"Has sido invitado como {suggested_role_name} a la finca {farm.name}",
        user_id=invited_user.user_id,
        notification_type_id=invitation_notification_type["notification_type_id"],
        invitation_id=invitation.invitation_id,
        notification_state_id=notification_pending_state["notification_state_id"],
        fcm_title="Nueva Invitación",
        fcm_body=f"Has sido invitado como {suggested_role_name} a la finca {farm.name}"
    )
    return None

def create_invitation(invitation_data, user, db: Session):
    # Validate farm and user access
    farm_data, error = _validate_farm_and_user_access(invitation_data, user)
    if error:
        return error

    # Validate role permissions
    suggested_role_name, error = _validate_role_permissions(invitation_data, farm_data["urf"])
    if error:
        return error

    # Validate invited user
    invited_user, error = _validate_invited_user(invitation_data, farm_data["urf_active_state_id"])
    if error:
        return error

    # Handle invitation creation or update
    try:
        new_invitation = _handle_invitation_creation_or_update(invitation_data, user, invited_user, db)

        # Send notification
        notification_error = _send_invitation_notification(new_invitation, invited_user, suggested_role_name, farm_data["farm"])
        if notification_error:
            return notification_error

    except Exception as e:
        db.rollback()
        logger.error(f"Error creando la invitación: {str(e)}")
        return create_response("error", f"Error creando la invitación: {str(e)}", status_code=500)

    return create_response("success", "Invitación creada exitosamente", {"invitation_id": new_invitation.invitation_id}, status_code=201)
