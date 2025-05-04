from sqlalchemy.orm import Session
from utils.response import create_response
from utils.state import get_invitation_state
from datetime import datetime
import pytz
import logging

# Import models as needed
from models.models import Invitations

bogota_tz = pytz.timezone("America/Bogota")
logger = logging.getLogger(__name__)

def create_invitation(invitation_data, user, db: Session):
    
    # Verificar si la finca existe
    farm = db.query(Farms).filter(Farms.farm_id == invitation_data.farm_id).first()
    if not farm:
        return create_response("error", "Finca no encontrada", status_code=404)

    # Verificar si el usuario (invitador) está asociado a la finca y cuál es su rol
    urf_active_state = get_state(db, "Activo", "user_role_farm")
    if not urf_active_state:
        return create_response("error", "El estado 'Activo' no fue encontrado para 'user_role_farm'", status_code=400)

    user_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == user.user_id,
        UserRoleFarm.farm_id == invitation_data.farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()

    if not user_role_farm:
        return create_response("error", "No tienes acceso a esta finca", status_code=403)

    # Verificar si el rol sugerido para la invitación es válido
    suggested_role = db.query(Roles).filter(Roles.name == invitation_data.suggested_role).first()
    if not suggested_role:
        return create_response("error", "El rol sugerido no es válido", status_code=400)

    # Verificar si el rol del usuario (invitador) tiene el permiso adecuado para invitar al rol sugerido
    if suggested_role.name == "Administrador de finca":
        has_permission_to_invite = db.query(RolePermission).join(Permissions).filter(
            RolePermission.role_id == user_role_farm.role_id,
            Permissions.name == "add_administrator_farm"
        ).first()
        if not has_permission_to_invite:
            return create_response("error", "No tienes permiso para invitar a un Administrador de Finca", status_code=403)

    elif suggested_role.name == "Operador de campo":
        has_permission_to_invite = db.query(RolePermission).join(Permissions).filter(
            RolePermission.role_id == user_role_farm.role_id,
            Permissions.name == "add_operator_farm"
        ).first()
        if not has_permission_to_invite:
            return create_response("error", "No tienes permiso para invitar a un Operador de Campo", status_code=403)

    else:
        return create_response("error", f"No puedes invitar a colaboradores de rol {suggested_role.name} ", status_code=403)

    # Verificar si el usuario ya está registrado
    existing_user = db.query(Users).filter(Users.email == invitation_data.email).first()
    if not existing_user:
        return create_response("error", "El usuario no está registrado", status_code=404)

    # Verificar si el usuario ya pertenece a la finca
    urf_active_state = get_state(db, "Activo", "user_role_farm")
    if not urf_active_state:
        return create_response("error", "El estado 'Activo' no fue encontrado para 'user_role_farm'", status_code=400)

    existing_role_farm = db.query(UserRoleFarm).filter(
        UserRoleFarm.user_id == existing_user.user_id,
        UserRoleFarm.farm_id == invitation_data.farm_id,
        UserRoleFarm.user_role_farm_state_id == urf_active_state.user_role_farm_state_id
    ).first()

    if existing_role_farm:
        return create_response("error", "El usuario ya está asociado a la finca con un estado activo", status_code=400)

    # Verificar si el usuario ya tiene una invitación pendiente
    invitation_pending_state = get_invitation_state(db, "Pendiente")
    if not invitation_pending_state:
        return create_response("error", "El estado 'Pendiente' no fue encontrado para 'Invitations'", status_code=400)

    existing_invitation = db.query(Invitations).filter(
        Invitations.email == invitation_data.email,
        Invitations.farm_id == invitation_data.farm_id,
        Invitations.invitation_state_id == invitation_pending_state.invitation_state_id
    ).first()

    if existing_invitation:
        return create_response("error", "El usuario ya tiene una invitación pendiente para esta finca", status_code=400)

    # Crear la invitación y la notificación solo después de todas las verificaciones
    try:
        # Crear la nueva invitación
        new_invitation = Invitations(
            email=invitation_data.email,
            suggested_role_id=suggested_role.role_id,
            farm_id=invitation_data.farm_id,
            inviter_user_id=user.user_id,
            invitation_date=datetime.now(bogota_tz)
        )
        db.add(new_invitation)
        db.commit()
        db.refresh(new_invitation)

        # Crear la notificación asociada con notification_type_id
        notification_pending_state = get_state(db, "Pendiente", "Notifications")
        if not notification_pending_state:
            db.rollback()
            logger.error("El estado 'Pendiente' no fue encontrado para 'Notifications'")
            return create_response("error", "El estado 'Pendiente' no fue encontrado para 'Notifications'", status_code=400)

        invitation_notification_type = db.query(NotificationTypes).filter(NotificationTypes.name == "Invitations").first()
        if not invitation_notification_type:
            db.rollback()
            logger.error("No se encontró el tipo de notificación 'Invitations'")
            return create_response("error", "No se encontró el tipo de notificación 'Invitations'", status_code=400)

        new_notification = Notifications(
            message=f"Has sido invitado como {invitation_data.suggested_role} a la finca {farm.name}",
            date=datetime.now(bogota_tz),
            user_id=existing_user.user_id,
            notification_type_id=invitation_notification_type.notification_type_id,
            invitation_id=new_invitation.invitation_id,
            farm_id=invitation_data.farm_id,
            notification_state_id=notification_pending_state.notification_state_id
        )
        db.add(new_notification)
        db.commit()

        # Enviar notificación FCM al usuario
        if fcm_token := existing_user.fcm_token:
            title = "Nueva Invitación"
            body = f"Has sido invitado como {invitation_data.suggested_role} a la finca {farm.name}"
            send_fcm_notification(fcm_token, title, body)
        else:
            logger.warning("No se pudo enviar la notificación push. No se encontró el token FCM del usuario.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando la invitación: {str(e)}")
        return create_response("error", f"Error creando la invitación: {str(e)}", status_code=500)

    return create_response("success", "Invitación creada exitosamente", {"invitation_id": new_invitation.invitation_id}, status_code=201)
