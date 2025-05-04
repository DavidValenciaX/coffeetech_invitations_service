from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from utils.security import verify_session_token
from dataBase import get_db_session
import logging
from utils.FCM import send_fcm_notification
from models.models import Invitations
from utils.response import create_response, session_token_invalid_response
from utils.state import get_invitation_state
import pytz
from datetime import datetime
from use_cases.create_invitation_use_case import create_invitation

bogota_tz = pytz.timezone("America/Bogota")

logger = logging.getLogger(__name__)

router = APIRouter()

class InvitationCreate(BaseModel):
    """
    Modelo para la creación de una invitación.

    Attributes:
        email (EmailStr): Dirección de correo electrónico del usuario a invitar.
        suggested_role_id (int): ID del rol sugerido para el usuario invitado.
        farm_id (int): Identificador de la finca a la que se invita.
    """
    email: EmailStr
    suggested_role_id: int
    farm_id: int

@router.post("/create-invitation")
def create_invitation_endpoint(invitation_data: InvitationCreate, session_token: str, db: Session = Depends(get_db_session)):
    """
    Crea una invitación para un usuario a una finca.

    Args:
        invitation_data (InvitationCreate): Datos de la invitación a crear.
        session_token (str): Token de sesión del usuario autenticado.
        db (Session): Sesión de base de datos.

    Returns:
        JSONResponse: Respuesta con el resultado de la creación de la invitación.
    """
    # Validar el session_token y obtener el usuario autenticado (el invitador)
    user = verify_session_token(session_token, db)
    if not user:
        return session_token_invalid_response()
    
    return create_invitation(invitation_data, user, db)

@router.post("/respond-invitation/{invitation_id}")
def respond_invitation_endpoint(invitation_id: int, action: str, session_token: str, db: Session = Depends(get_db_session)):
    """
    Responde a una invitación con las acciones 'accept' o 'reject'.
    
    Parámetros:
    - invitation_id: ID de la invitación a procesar.
    - action: La acción a realizar ('accept' o 'reject').
    - session_token: Token de sesión del usuario autenticado.
    - db: Sesión de la base de datos (inyectada mediante Depends).
    
    Retorna:
    - Un mensaje de éxito o error en función de la acción realizada.
    """
    # Validar el session_token y obtener el usuario autenticado
    user = verify_session_token(session_token, db)
    if not user:
        return session_token_invalid_response()

    # Buscar la invitación
    invitation = db.query(Invitations).filter(Invitations.invitation_id == invitation_id).first()
    if not invitation:
        return create_response("error", "Invitación no encontrada", status_code=404)
    
    # Verificar si el usuario es el invitado
    if user.email != invitation.email:
        return create_response("error", "No tienes permiso para responder esta invitación", status_code=403)

    # Usar get_invitation_state para obtener los estados "Aceptada" y "Rechazada"
    accepted_invitation_state = get_invitation_state(db, "Aceptada")
    rejected_invitation_state = get_invitation_state(db, "Rechazada")
    responded_notification_state = get_state(db, "Respondida", "Notifications")  # Obtener el estado "Respondida"

    if not accepted_invitation_state or not rejected_invitation_state or not responded_notification_state:
        return create_response("error", "Estados necesarios no encontrados en la base de datos", status_code=500)

    # Verificar si la invitación ya fue aceptada o rechazada
    if invitation.invitation_state_id in [accepted_invitation_state.invitation_state_id, rejected_invitation_state.invitation_state_id]:
        return create_response("error", "La invitación ya ha sido procesada (aceptada o rechazada)", status_code=400)

    # Actualizar las notificaciones relacionadas con la invitación
    notification = db.query(Notifications).filter(Notifications.invitation_id == invitation_id).first()
    if notification:
        notification.notification_state_id = responded_notification_state.notification_state_id  # Actualizar el estado a "Respondida"
        db.commit()

    # Verificar si la acción es "accept" o "reject"
    if action.lower() == "accept":
        # Cambiar el estado de la invitación a "Aceptada"
        invitation.invitation_state_id = accepted_invitation_state.invitation_state_id
        db.commit()

        # Usar la función get_state para obtener el estado "Activo" del tipo "user_role_farm"
        urf_active_state = get_state(db, "Activo", "user_role_farm")
        if not urf_active_state:
            return create_response("error", "El estado 'Activo' no fue encontrado para 'user_role_farm'", status_code=400)

        # Obtener el rol sugerido
        suggested_role = db.query(Roles).filter(Roles.name == invitation.suggested_role).first()
        if not suggested_role:
            return create_response("error", "El rol sugerido no es válido", status_code=400)

        # Agregar al usuario a la finca en la tabla UserRoleFarm con el rol de la invitación
        new_user_role_farm = UserRoleFarm(
            user_id=user.user_id,
            farm_id=invitation.farm_id,
            role_id=suggested_role.role_id,  # Asignar el rol sugerido
            user_role_farm_state_id=urf_active_state.user_role_farm_state_id  # Estado "Activo" del tipo "user_role_farm"
        )
        db.add(new_user_role_farm)
        db.commit()

        # Crear la notificación para el usuario que hizo la invitación (inviter_user_id)
        inviter = db.query(Users).filter(Users.user_id == invitation.inviter_user_id).first()
        if inviter:
            accepted_notification_type = db.query(NotificationTypes).filter(NotificationTypes.name == "Invitation_accepted").first()
            if not accepted_notification_type:
                return create_response("error", "No se encontró el tipo de notificación 'Invitation_accepted'", status_code=400)

            notification_message = f"El usuario {user.name} ha aceptado tu invitación a la finca {invitation.farm.name}."
            new_notification = Notifications(
                message=notification_message,
                date=datetime.now(bogota_tz),
                user_id=invitation.inviter_user_id,
                notification_type_id=accepted_notification_type.notification_type_id,
                invitation_id=invitation.invitation_id,
                farm_id=invitation.farm_id,
                notification_state_id=responded_notification_state.notification_state_id
            )
            db.add(new_notification)
            db.commit()

            # Enviar notificación FCM al invitador (si tiene token)
            if inviter.fcm_token:
                send_fcm_notification(inviter.fcm_token, "Invitación aceptada", notification_message)

        return create_response("success", "Has aceptado la invitación exitosamente", status_code=200)

    elif action.lower() == "reject":
        # Cambiar el estado de la invitación a "Rechazada"
        invitation.invitation_state_id = rejected_invitation_state.invitation_state_id
        db.commit()

        # Crear la notificación para el usuario que hizo la invitación (inviter_user_id)
        inviter = db.query(Users).filter(Users.user_id == invitation.inviter_user_id).first()
        if inviter:
            rejected_notification_type = db.query(NotificationTypes).filter(NotificationTypes.name == "invitation_rejected").first()
            if not rejected_notification_type:
                return create_response("error", "No se encontró el tipo de notificación 'invitation_rejected'", status_code=400)

            notification_message = f"El usuario {user.name} ha rechazado tu invitación a la finca {invitation.farm.name}."
            new_notification = Notifications(
                message=notification_message,
                date=datetime.now(bogota_tz),
                user_id=invitation.inviter_user_id,
                notification_type_id=rejected_notification_type.notification_type_id,  # Usar notification_type_id
                invitation_id=invitation.invitation_id,
                farm_id=invitation.farm_id,
                notification_state_id=responded_notification_state.notification_state_id  # Estado "Respondida" del tipo "Notifications"
            )
            db.add(new_notification)
            db.commit()

            # Enviar notificación FCM al invitador (si tiene token)
            if inviter.fcm_token:
                send_fcm_notification(inviter.fcm_token, "Invitación rechazada", notification_message)

        return create_response("success", "Has rechazado la invitación exitosamente", status_code=200)

    else:
        return create_response("error", "Acción inválida. Debes usar 'accept' o 'reject'", status_code=400)