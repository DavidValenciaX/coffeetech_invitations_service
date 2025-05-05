from sqlalchemy.orm import Session
from utils.response import create_response
from utils.state import get_invitation_state
from datetime import datetime
from adapters.farm_client import get_farm_by_id, get_user_role_farm
from adapters.user_client import get_role_name_by_id, get_role_permissions_for_user_role, user_verification_by_email
import pytz
import logging
from adapters.notification_client import get_notification_state_by_name, get_notification_type_by_name, get_user_devices_by_user_id, send_notification

# Import models as needed
from models.models import Invitations

bogota_tz = pytz.timezone("America/Bogota")

logger = logging.getLogger(__name__)

def create_invitation(invitation_data, user, db: Session):
    # Verificar si la finca existe
    farm = get_farm_by_id(invitation_data.farm_id)
    if farm is None:
        return create_response("error", "Finca no encontrada", status_code=404)

    # Obtener user_role_farm y su estado desde el farm service
    urf = get_user_role_farm(user.user_id, invitation_data.farm_id)
    if not urf or urf.user_role_farm_state != "Activo":
        return create_response("error", "No tienes acceso a esta finca", status_code=403)

    # Obtener el nombre del rol sugerido usando el microservicio de usuarios
    suggested_role_name = get_role_name_by_id(invitation_data.suggested_role_id)
    if not suggested_role_name:
        return create_response("error", "El rol sugerido no es válido", status_code=400)

    # Validar permisos del usuario invitador usando el microservicio de usuarios
    inviter_permissions = get_role_permissions_for_user_role(urf.user_role_id)
    if suggested_role_name == "Administrador de finca":
        if "add_administrator_farm" not in inviter_permissions:
            return create_response("error", "No tienes permiso para invitar a un Administrador de Finca", status_code=403)
    elif suggested_role_name == "Operador de campo":
        if "add_operator_farm" not in inviter_permissions:
            return create_response("error", "No tienes permiso para invitar a un Operador de Campo", status_code=403)
    else:
        return create_response("error", f"No puedes invitar a colaboradores de rol {suggested_role_name} ", status_code=403)

    # Verificar si el usuario ya está registrado usando el microservicio de usuarios
    invited_user = user_verification_by_email(invitation_data.email)
    if not invited_user:
        return create_response("error", "El usuario no está registrado", status_code=404)

    # Verificar si el usuario ya pertenece a la finca (consultando el microservicio de fincas)
    urf_invited = get_user_role_farm(invited_user.user_id, invitation_data.farm_id)
    if urf_invited and urf_invited.user_role_farm_state == "Activo":
        return create_response("error", "El usuario ya está asociado a la finca con un estado activo", status_code=400)

    # Verificar si el usuario ya tiene una invitación pendiente
    invitation_pending_state = get_invitation_state(db, "Pendiente")
    if not invitation_pending_state:
        return create_response("error", "El estado 'Pendiente' no fue encontrado para 'Invitations'", status_code=400)

    existing_invitation = db.query(Invitations).filter(
        Invitations.invited_user_id == invited_user.user_id,
        Invitations.entity_type == "farm",
        Invitations.entity_id == invitation_data.farm_id,
        Invitations.invitation_state_id == invitation_pending_state.invitation_state_id
    ).first()

    if existing_invitation:
        return create_response("error", "El usuario ya tiene una invitación pendiente para esta finca", status_code=400)

    # Crear la invitación y la notificación solo después de todas las verificaciones
    try:
        # Crear la nueva invitación
        new_invitation = Invitations(
            invited_user_id=invited_user.user_id,
            suggested_role_id=invitation_data.suggested_role_id,
            entity_type="farm",
            entity_id=invitation_data.farm_id,
            inviter_user_id=user.user_id,
            invitation_date=datetime.now(bogota_tz),
            invitation_state_id=invitation_pending_state.invitation_state_id
        )
        db.add(new_invitation)

        # Obtener estado y tipo de notificación desde el microservicio de notificaciones
        notification_pending_state = get_notification_state_by_name("Pendiente")
        if not notification_pending_state:
            db.rollback()
            logger.error("El estado 'Pendiente' no fue encontrado para 'Notifications'")
            return create_response("error", "El estado 'Pendiente' no fue encontrado para 'Notifications'", status_code=400)

        invitation_notification_type = get_notification_type_by_name("Invitations")
        if not invitation_notification_type:
            db.rollback()
            logger.error("No se encontró el tipo de notificación 'Invitations'")
            return create_response("error", "No se encontró el tipo de notificación 'Invitations'", status_code=400)

        # Obtener todos los dispositivos del usuario invitado
        user_devices = get_user_devices_by_user_id(invited_user.user_id)
        if not user_devices:
            logger.warning(f"El usuario {invited_user.user_id} no tiene dispositivos registrados para notificaciones.")

        # Enviar la notificación a todos los dispositivos del usuario invitado
        for device in user_devices or []:
            send_notification(
                message=f"Has sido invitado como {suggested_role_name} a la finca {farm.name}",
                user_id=invited_user.user_id,
                notification_type_id=invitation_notification_type["notification_type_id"],
                entity_type="farm",
                entity_id=invitation_data.farm_id,
                notification_state_id=notification_pending_state["notification_state_id"],
                fcm_token=device["fcm_token"],
                fcm_title="Nueva Invitación",
                fcm_body=f"Has sido invitado como {suggested_role_name} a la finca {farm.name}"
            )
            
        # Commit at the end after all operations succeed
        db.commit()
        db.refresh(new_invitation)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando la invitación: {str(e)}")
        return create_response("error", f"Error creando la invitación: {str(e)}", status_code=500)

    return create_response("success", "Invitación creada exitosamente", {"invitation_id": new_invitation.invitation_id}, status_code=201)
