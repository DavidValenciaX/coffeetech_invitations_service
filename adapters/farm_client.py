from dotenv import load_dotenv
import os
import logging
import requests
from pydantic import BaseModel

load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

FARM_SERVICE_URL = os.getenv("FARMS_SERVICE_URL", "http://localhost:8002")

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

def get_farm_by_id(farm_id: int):
    """
    Solicita la información de una finca al servicio de farms.
    """
    url = f"{FARM_SERVICE_URL}/farms-service/get-farm/{farm_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Si la respuesta es un dict con los campos esperados, parsear con el modelo
        return FarmDetailResponse(**data)
    except Exception as e:
        logger.error(f"Error al consultar la finca: {e}")
        return {"status": "error", "message": f"Error al consultar la finca: {str(e)}"}

def get_user_role_farm(user_id: int, farm_id: int):
    """
    Solicita la relación user_role_farm y su estado al servicio de farms.
    """
    url = f"{FARM_SERVICE_URL}/farms-service/get-user-role-farm/{user_id}/{farm_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "status" in data and data["status"] == "error":
            return None
        return UserRoleFarmResponse(**data)
    except Exception as e:
        logger.error(f"Error al consultar user_role_farm: {e}")
        return None

def create_user_role_farm(user_role_id: int, farm_id: int, user_role_farm_state_id: int):
    """
    Crea la relación UserRoleFarm en el servicio de fincas.
    """
    url = f"{FARM_SERVICE_URL}/farms-service/create-user-role-farm"
    payload = {
        "user_role_id": user_role_id,
        "farm_id": farm_id,
        "user_role_farm_state_id": user_role_farm_state_id
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error al crear user_role_farm: {e}")
        return {"status": "error", "message": f"Error al crear user_role_farm: {str(e)}"}
