from pydantic import BaseModel, EmailStr

# --- From invitations.py ---
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

# --- From adapters/user_client.py ---
class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str

# --- From adapters/farm_client.py ---
class FarmDetailResponse(BaseModel):
    farm_id: int
    name: str
    area: float
    area_unit_id: int
    area_unit: str
    farm_state_id: int
    farm_state: str

class UserRoleFarmResponse(BaseModel):
    user_role_farm_id: int
    user_role_id: int
    farm_id: int
    user_role_farm_state_id: int
    user_role_farm_state: str
