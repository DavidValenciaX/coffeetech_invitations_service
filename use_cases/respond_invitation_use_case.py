from utils.response import create_response
from utils.state import get_invitation_state
from models.models import Invitations
from sqlalchemy.orm import Session
# Adapters para microservicios
from adapters.farm_client import get_farm_by_id, create_user_role_farm, get_user_role_farm_state_by_name
from adapters.user_client import get_role_name_by_id, create_user_role
from adapters.notification_client import (
    get_notification_state_by_name,
    get_notification_type_by_name,
    get_user_devices_by_user_id,
    update_notification_state,
    get_notification_id_by_invitation_id,
    send_notification
)
import pytz
import logging

logger = logging.getLogger(__name__)

bogota_tz = pytz.timezone("America/Bogota")

def respond_invitation(invitation_id: int, action: str, user, db: Session):
    # Buscar la invitación
    invitation = db.query(Invitations).filter(Invitations.invitation_id == invitation_id).first()
    if not invitation:
        return create_response("error", "Invitación no encontrada", status_code=404)

    # Verificar si el usuario es el invitado
    if user.user_id != invitation.invited_user_id:
        return create_response("error", "No tienes permiso para responder esta invitación", status_code=403)

    # Obtener estados desde microservicio
    accepted_invitation_state = get_invitation_state(db, "Aceptada")
    rejected_invitation_state = get_invitation_state(db, "Rechazada")

    if not accepted_invitation_state or not rejected_invitation_state:
        logger.error("Estados de invitación 'Aceptada' o 'Rechazada' no encontrados.")
        return create_response("error", "Estados necesarios no encontrados en la base de datos", status_code=500)

    # Verificar si la invitación ya fue aceptada o rechazada
    if invitation.invitation_state_id in [
        accepted_invitation_state.invitation_state_id,
        rejected_invitation_state.invitation_state_id,
    ]:
        return create_response("error", "La invitación ya ha sido procesada (aceptada o rechazada)", status_code=400)

    responded_notification_state = get_notification_state_by_name("Respondida")
    if not responded_notification_state:
        return create_response("error", "Estado de notificación respondida no encontrado", status_code=500)

    # Obtener notification_id desde el microservicio de notificaciones
    try:
        notification_id = get_notification_id_by_invitation_id(invitation_id)
    except Exception as e:
        notification_id = None

    if notification_id:
        update_notification_state(
            notification_id,
            responded_notification_state["notification_state_id"]
            if isinstance(responded_notification_state, dict)
            else responded_notification_state.notification_state_id
        )

    # Acción: aceptar invitación
    if action.lower() == "accept":
        # Crear la relación user-role-farm usando los microservicios ANTES de cambiar el estado y hacer commit
        suggested_role_name = get_role_name_by_id(invitation.suggested_role_id)
        if not suggested_role_name:
            return create_response("error", "El rol sugerido no es válido", status_code=400)
        try:
            # Crea el user_role en el microservicio de usuarios y obtiene el user_role_id
            user_role_response = create_user_role(user.user_id, suggested_role_name)
            user_role_id = user_role_response.get("user_role_id")
            if not user_role_id:
                return create_response("error", "No se pudo obtener el user_role_id", status_code=500)

            # Obtener el estado "Activo" para UserRoleFarm desde el microservicio de fincas
            urf_active_state = get_user_role_farm_state_by_name("Activo")
            if not urf_active_state or not urf_active_state.get("user_role_farm_state_id"):
                return create_response("error", "No se pudo obtener el estado 'Activo' para UserRoleFarm", status_code=500)
            urf_active_state_id = urf_active_state["user_role_farm_state_id"]

            # Crear la relación UserRoleFarm en el microservicio de fincas
            urf_response = create_user_role_farm(user_role_id, invitation.entity_id, urf_active_state_id)
            if not urf_response or urf_response.get("status") != "success":
                return create_response("error", f"No se pudo asociar el usuario a la finca: {urf_response}", status_code=500)
        except Exception as e:
            return create_response("error", f"No se pudo asociar el usuario a la finca: {str(e)}", status_code=500)

        # Cambiar el estado de la invitación a "Aceptada" y hacer commit SOLO después de que todo lo anterior haya funcionado
        invitation.invitation_state_id = accepted_invitation_state.invitation_state_id
        db.commit()

        # Notificar al invitador
        inviter_user_id = invitation.inviter_user_id
        inviter_devices = get_user_devices_by_user_id(inviter_user_id)
        accepted_notification_type = get_notification_type_by_name("Invitation_accepted")
        farm = get_farm_by_id(invitation.entity_id)
        if farm is None:
            return create_response("error", "Finca no encontrada", status_code=404)
        notification_message = f"El usuario {user.name} ha aceptado tu invitación a la finca {farm.name}."
        for device in inviter_devices or []:
            send_notification(
                message=notification_message,
                user_id=inviter_user_id,
                notification_type_id=accepted_notification_type["notification_type_id"] if accepted_notification_type else None,
                entity_type="farm",
                entity_id=invitation.entity_id,
                notification_state_id=responded_notification_state["notification_state_id"],
                fcm_token=device["fcm_token"],
                fcm_title="Invitación aceptada",
                fcm_body=notification_message,
            )

        return create_response("success", "Has aceptado la invitación exitosamente", status_code=200)

    # Acción: rechazar invitación
    elif action.lower() == "reject":
        # Cambiar el estado de la invitación a "Rechazada"
        invitation.invitation_state_id = rejected_invitation_state.invitation_state_id
        db.commit()

        # Notificar al invitador
        inviter_user_id = invitation.inviter_user_id
        inviter_devices = get_user_devices_by_user_id(inviter_user_id)
        rejected_notification_type = get_notification_type_by_name("invitation_rejected")
        farm = get_farm_by_id(invitation.entity_id)
        if farm is None:
            return create_response("error", "Finca no encontrada", status_code=404)
        notification_message = f"El usuario {user.name} ha rechazado tu invitación a la finca {farm.name}."
        for device in inviter_devices or []:
            send_notification(
                message=notification_message,
                user_id=inviter_user_id,
                notification_type_id=rejected_notification_type["notification_type_id"] if rejected_notification_type else None,
                entity_type="farm",
                entity_id=invitation.entity_id,
                notification_state_id=responded_notification_state["notification_state_id"],
                fcm_token=device["fcm_token"],
                fcm_title="Invitación rechazada",
                fcm_body=notification_message,
            )

        return create_response("success", "Has rechazado la invitación exitosamente", status_code=200)

    else:
        return create_response("error", "Acción inválida. Debes usar 'accept' o 'reject'", status_code=400)
