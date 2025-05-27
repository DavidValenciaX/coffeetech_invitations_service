from typing import Optional, Any, Dict, Union
from dotenv import load_dotenv
from domain.schemas import UserResponse
import httpx
import logging
import os

# Load environment variables
load_dotenv(override=True, encoding="utf-8")

logger = logging.getLogger(__name__)

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 10.0

class UserRoleCreationError(Exception):
    """Custom exception for errors during user role creation."""
    pass

def _make_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT
) -> Optional[Dict[str, Any]]:
    """
    Base function to make HTTP requests to the user service.
    
    Args:
        endpoint (str): The API endpoint to call (without base URL)
        method (str): HTTP method to use ('GET', 'POST', etc.)
        data (dict, optional): JSON data to send in the request body
        params (dict, optional): Query parameters to include in the request
        timeout (float): Request timeout in seconds
        
    Returns:
        dict: Response data as dictionary if successful, None otherwise
    """
    url = f"{USER_SERVICE_URL}{endpoint}"
    
    try:
        with httpx.Client(timeout=timeout) as client:
            if method.upper() == "GET":
                response = client.get(url, params=params)
            elif method.upper() == "POST":
                response = client.post(url, json=data)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            if response.status_code in (200, 201):
                return response.json()
            else:
                logger.error(f"Error calling {url}: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        logger.error(f"Exception calling {url}: {str(e)}")
        return None

def verify_session_token(session_token: str) -> Optional[Union[Dict[str, Any], UserResponse]]:
    """
    Verifies a session token by making a request to the user service.
    Returns user data if the token is valid, None otherwise.
    
    Args:
        session_token (str): Session token to verify
        
    Returns:
        UserResponse: User data object if token is valid, None otherwise
    """
    response = _make_request(
        "/users-service/session-token-verification", 
        method="POST", 
        data={"session_token": session_token}
    )
    
    if response and response.get("status") == "success" and "user" in response.get("data", {}):
        # Convertir diccionario a objeto Pydantic
        return UserResponse(**response["data"]["user"])
    return None

def user_verification_by_email(email: str):
    """
    Consulta el microservicio de usuarios para verificar si existe un usuario con el email dado.
    Retorna el objeto usuario si existe, None si no.
    """
    response = _make_request("/users-service/user-verification-by-email", method="POST", data={"email": email})
    if response and response.get("status") == "success" and "user" in response.get("data", {}):
        return UserResponse(**response["data"]["user"])
    return None

def create_user_role(user_id: int, role_name: str) -> dict:
    """
    Creates a UserRole for the given user in the user service.

    Args:
        user_id (int): The user ID.
        role_name (str): The role name to assign.

    Returns:
        dict: The response data from the user service.

    Raises:
        Exception: If the request fails or response is invalid.
    """
    response = _make_request(
        "/users-service/user-role",
        method="POST",
        data={"user_id": user_id, "role_name": role_name}
    )
    if response and "user_role_id" in response:
        return response
    else:
        raise UserRoleCreationError(f"Error creating user_role for user {user_id} with role '{role_name}': {response}")

def get_role_permissions_for_user_role(user_role_id: int) -> list:
    """
    Gets the list of permission names for a given user_role_id from the user service.

    Args:
        user_role_id (int): ID of the UserRole entry

    Returns:
        list: List of permission names (str)
    """
    response = _make_request(f"/users-service/user-role/{user_role_id}/permissions")
    if response and "permissions" in response:
        return [perm["name"] for perm in response["permissions"]]
    return []

def get_role_name_by_id(role_id: int) -> Optional[str]:
    """
    Gets the role name for a given role_id from the user service.

    Args:
        role_id (int): ID of the Role

    Returns:
        str: The name of the role, or None if not found or error occurs.
    """
    response = _make_request(f"/users-service/{role_id}/name")
    if response and "role_name" in response:
        return response["role_name"]
    logger.error(f"Could not retrieve role name for role_id {role_id}")
    return None