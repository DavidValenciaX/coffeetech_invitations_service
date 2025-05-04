from dotenv import load_dotenv
import os
import logging
import requests

load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

FARM_SERVICE_URL = os.getenv("FARMS_SERVICE_URL", "http://localhost:8002")

def get_farm_by_id(farm_id: int):
    """
    Solicita la información de una finca al servicio de farms.
    """
    url = f"{FARM_SERVICE_URL}/farm/get-farm/{farm_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error al consultar la finca: {e}")
        return {"status": "error", "message": f"Error al consultar la finca: {str(e)}"}
