from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dataBase import get_db_session
import logging
import pytz

from models.models import Invitations
from utils.response import create_response

bogota_tz = pytz.timezone("America/Bogota")

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{invitation_id}",
    response_model=dict,
    responses={
        200: {
            "description": "Detalles de la invitación",
            "content": {
                "application/json": {
                    "example": {
                        "invitation_id": 1,
                        "invited_user_id": 2,
                        "suggested_role_id": 3,
                        "invitation_state_id": 1,
                        "farm_id": 4,
                        "inviter_user_id": 5,
                        "invitation_date": "2023-10-25T14:30:00Z"
                    }
                }
            }
        },
        404: {
            "description": "Invitación no encontrada",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "message": "Invitación no encontrada",
                        "data": None
                    }
                }
            }
        }
    }
)
def get_invitation_details(invitation_id: int, db: Session = Depends(get_db_session)):
    """
    Obtener los detalles de una invitación por su ID.
    
    Args:
        invitation_id: ID de la invitación a consultar
        db: Sesión de base de datos
        
    Returns:
        Detalles de la invitación si existe
    """
    invitation = db.query(Invitations).filter(Invitations.invitation_id == invitation_id).first()
    
    if not invitation:
        return create_response("error", "Invitación no encontrada", status_code=404)
    
    return {
        "invitation_id": invitation.invitation_id,
        "invited_user_id": invitation.invited_user_id,
        "suggested_role_id": invitation.suggested_role_id,
        "invitation_state_id": invitation.invitation_state_id,
        "farm_id": invitation.farm_id,
        "inviter_user_id": invitation.inviter_user_id,
        "invitation_date": invitation.invitation_date
    }