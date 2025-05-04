from sqlalchemy.orm import Session
from models.models import InvitationStates
import logging

logger = logging.getLogger(__name__)

def get_invitation_state(db: Session, state_name: str):
    """
    Obtiene el estado para las invitaciones.

    Args:
        db (Session): Sesión de la base de datos.
        state_name (str): Nombre del estado a obtener (e.g., "Pendiente", "Aceptada", "Rechazada").

    Returns:
        El objeto InvitationStates si se encuentra, None en caso contrario.
    """
    try:
        return db.query(InvitationStates).filter(InvitationStates.name == state_name).first()
    except Exception as e:
        logger.error(f"Error al obtener el estado de invitación '{state_name}': {str(e)}")
        return None
