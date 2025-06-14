from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from adapters.user_client import verify_session_token
from dataBase import get_db_session
from utils.response import session_token_invalid_response
from use_cases.create_invitation_use_case import create_invitation
from use_cases.respond_invitation_use_case import respond_invitation
from domain.schemas import InvitationCreate
import logging
import pytz

bogota_tz = pytz.timezone("America/Bogota")

logger = logging.getLogger(__name__)

router = APIRouter()

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
    user = verify_session_token(session_token)
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
    user = verify_session_token(session_token)
    if not user:
        return session_token_invalid_response()

    # Llama al use case para manejar la lógica de respuesta
    return respond_invitation(invitation_id, action, user, db)