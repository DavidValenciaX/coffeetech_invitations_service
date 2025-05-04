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
