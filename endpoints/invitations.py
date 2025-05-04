from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from utils.security import verify_session_token
from dataBase import get_db_session
import logging
from utils.response import session_token_invalid_response
import pytz
from use_cases.create_invitation_use_case import create_invitation
from use_cases.respond_invitation_use_case import respond_invitation

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

    # Llama al use case para manejar la lógica de respuesta
    return respond_invitation(invitation_id, action, user, db)