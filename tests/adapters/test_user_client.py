import pytest
from unittest.mock import patch, Mock, MagicMock
import httpx
from adapters.user_client import (
    _make_request,
    verify_session_token,
    user_verification_by_email,
    create_user_role,
    get_role_permissions_for_user_role,
    get_role_name_by_id,
    UserRoleCreationError,
    USER_SERVICE_URL,
    DEFAULT_TIMEOUT
)
from domain.schemas import UserResponse


class TestMakeRequest:
    """Tests for the _make_request function."""
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_get_success(self, mock_client):
        """Test successful GET request."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = _make_request("/test", method="GET", params={"param": "value"})
        
        # Assert
        assert result == {"data": "test"}
        mock_client_instance.get.assert_called_once_with(
            f"{USER_SERVICE_URL}/test", 
            params={"param": "value"}
        )
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_post_success(self, mock_client):
        """Test successful POST request."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"created": True}
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = _make_request("/test", method="POST", data={"key": "value"})
        
        # Assert
        assert result == {"created": True}
        mock_client_instance.post.assert_called_once_with(
            f"{USER_SERVICE_URL}/test", 
            json={"key": "value"}
        )
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_error_status(self, mock_client):
        """Test request with error status code."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = _make_request("/test")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_exception(self, mock_client):
        """Test request that raises an exception."""
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.get.side_effect = httpx.RequestError("Connection error")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = _make_request("/test")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_unsupported_method(self, mock_client):
        """Test request with unsupported HTTP method."""
        # Act
        result = _make_request("/test", method="DELETE")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client.httpx.Client')
    def test_make_request_custom_timeout(self, mock_client):
        """Test request with custom timeout."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = _make_request("/test", timeout=30.0)
        
        # Assert
        assert result == {"data": "test"}
        mock_client.assert_called_once_with(timeout=30.0)


class TestVerifySessionToken:
    """Tests for the verify_session_token function."""
    
    @patch('adapters.user_client._make_request')
    def test_verify_session_token_success(self, mock_make_request):
        """Test successful session token verification."""
        # Arrange
        mock_make_request.return_value = {
            "status": "success",
            "data": {
                "user": {
                    "user_id": 1,
                    "name": "John Doe",
                    "email": "john@example.com"
                }
            }
        }
        
        # Act
        result = verify_session_token("valid_token")
        
        # Assert
        assert isinstance(result, UserResponse)
        assert result.user_id == 1
        assert result.name == "John Doe"
        assert result.email == "john@example.com"
        mock_make_request.assert_called_once_with(
            "/users-service/session-token-verification",
            method="POST",
            data={"session_token": "valid_token"}
        )
    
    @patch('adapters.user_client._make_request')
    def test_verify_session_token_invalid_response(self, mock_make_request):
        """Test session token verification with invalid response."""
        # Arrange
        mock_make_request.return_value = {
            "status": "error",
            "message": "Invalid token"
        }
        
        # Act
        result = verify_session_token("invalid_token")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_verify_session_token_no_user_data(self, mock_make_request):
        """Test session token verification with missing user data."""
        # Arrange
        mock_make_request.return_value = {
            "status": "success",
            "data": {}
        }
        
        # Act
        result = verify_session_token("token")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_verify_session_token_request_failure(self, mock_make_request):
        """Test session token verification when request fails."""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = verify_session_token("token")
        
        # Assert
        assert result is None


class TestUserVerificationByEmail:
    """Tests for the user_verification_by_email function."""
    
    @patch('adapters.user_client._make_request')
    def test_user_verification_by_email_success(self, mock_make_request):
        """Test successful user verification by email."""
        # Arrange
        mock_make_request.return_value = {
            "status": "success",
            "data": {
                "user": {
                    "user_id": 2,
                    "name": "Jane Smith",
                    "email": "jane@example.com"
                }
            }
        }
        
        # Act
        result = user_verification_by_email("jane@example.com")
        
        # Assert
        assert isinstance(result, UserResponse)
        assert result.user_id == 2
        assert result.name == "Jane Smith"
        assert result.email == "jane@example.com"
        mock_make_request.assert_called_once_with(
            "/users-service/user-verification-by-email",
            method="POST",
            data={"email": "jane@example.com"}
        )
    
    @patch('adapters.user_client._make_request')
    def test_user_verification_by_email_not_found(self, mock_make_request):
        """Test user verification by email when user not found."""
        # Arrange
        mock_make_request.return_value = {
            "status": "error",
            "message": "User not found"
        }
        
        # Act
        result = user_verification_by_email("notfound@example.com")
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_user_verification_by_email_request_failure(self, mock_make_request):
        """Test user verification by email when request fails."""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = user_verification_by_email("test@example.com")
        
        # Assert
        assert result is None


class TestCreateUserRole:
    """Tests for the create_user_role function."""
    
    @patch('adapters.user_client._make_request')
    def test_create_user_role_success(self, mock_make_request):
        """Test successful user role creation."""
        # Arrange
        mock_make_request.return_value = {
            "user_role_id": 123,
            "user_id": 1,
            "role_name": "admin"
        }
        
        # Act
        result = create_user_role(1, "admin")
        
        # Assert
        assert result == {
            "user_role_id": 123,
            "user_id": 1,
            "role_name": "admin"
        }
        mock_make_request.assert_called_once_with(
            "/users-service/user-role",
            method="POST",
            data={"user_id": 1, "role_name": "admin"}
        )
    
    @patch('adapters.user_client._make_request')
    def test_create_user_role_failure(self, mock_make_request):
        """Test user role creation failure."""
        # Arrange
        mock_make_request.return_value = {
            "error": "Role not found"
        }
        
        # Act & Assert
        with pytest.raises(UserRoleCreationError) as exc_info:
            create_user_role(1, "invalid_role")
        
        assert "Error creating user_role for user 1 with role 'invalid_role'" in str(exc_info.value)
    
    @patch('adapters.user_client._make_request')
    def test_create_user_role_request_failure(self, mock_make_request):
        """Test user role creation when request fails."""
        # Arrange
        mock_make_request.return_value = None
        
        # Act & Assert
        with pytest.raises(UserRoleCreationError):
            create_user_role(1, "admin")


class TestGetRolePermissionsForUserRole:
    """Tests for the get_role_permissions_for_user_role function."""
    
    @patch('adapters.user_client._make_request')
    def test_get_role_permissions_success(self, mock_make_request):
        """Test successful retrieval of role permissions."""
        # Arrange
        mock_make_request.return_value = {
            "permissions": [
                {"name": "read_users", "id": 1},
                {"name": "write_users", "id": 2},
                {"name": "delete_users", "id": 3}
            ]
        }
        
        # Act
        result = get_role_permissions_for_user_role(123)
        
        # Assert
        assert result == ["read_users", "write_users", "delete_users"]
        mock_make_request.assert_called_once_with(
            "/users-service/user-role/123/permissions"
        )
    
    @patch('adapters.user_client._make_request')
    def test_get_role_permissions_no_permissions(self, mock_make_request):
        """Test retrieval when no permissions found."""
        # Arrange
        mock_make_request.return_value = {
            "error": "User role not found"
        }
        
        # Act
        result = get_role_permissions_for_user_role(999)
        
        # Assert
        assert result == []
    
    @patch('adapters.user_client._make_request')
    def test_get_role_permissions_request_failure(self, mock_make_request):
        """Test retrieval when request fails."""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = get_role_permissions_for_user_role(123)
        
        # Assert
        assert result == []
    
    @patch('adapters.user_client._make_request')
    def test_get_role_permissions_empty_permissions(self, mock_make_request):
        """Test retrieval with empty permissions list."""
        # Arrange
        mock_make_request.return_value = {
            "permissions": []
        }
        
        # Act
        result = get_role_permissions_for_user_role(123)
        
        # Assert
        assert result == []


class TestGetRoleNameById:
    """Tests for the get_role_name_by_id function."""
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_success(self, mock_make_request):
        """Test successful retrieval of role name."""
        # Arrange
        mock_make_request.return_value = {
            "role_name": "administrator"
        }
        
        # Act
        result = get_role_name_by_id(1)
        
        # Assert
        assert result == "administrator"
        mock_make_request.assert_called_once_with(
            "/users-service/1/name"
        )
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_not_found(self, mock_make_request):
        """Test retrieval when role not found."""
        # Arrange
        mock_make_request.return_value = {
            "error": "Role not found"
        }
        
        # Act
        result = get_role_name_by_id(999)
        
        # Assert
        assert result is None
    
    @patch('adapters.user_client._make_request')
    def test_get_role_name_request_failure(self, mock_make_request):
        """Test retrieval when request fails."""
        # Arrange
        mock_make_request.return_value = None
        
        # Act
        result = get_role_name_by_id(1)
        
        # Assert
        assert result is None


class TestConstants:
    """Tests for module constants and configuration."""
    
    def test_default_timeout_value(self):
        """Test that default timeout is set correctly."""
        assert DEFAULT_TIMEOUT == pytest.approx(10.0)
    
    def test_user_service_url_default(self):
        """Test that USER_SERVICE_URL has a default value."""
        assert USER_SERVICE_URL is not None
        assert isinstance(USER_SERVICE_URL, str)
        assert USER_SERVICE_URL.startswith('http')


class TestUserRoleCreationError:
    """Tests for the UserRoleCreationError exception."""
    
    def test_user_role_creation_error_inheritance(self):
        """Test that UserRoleCreationError inherits from Exception."""
        assert issubclass(UserRoleCreationError, Exception)
    
    def test_user_role_creation_error_message(self):
        """Test that UserRoleCreationError can be raised with a message."""
        message = "Test error message"
        with pytest.raises(UserRoleCreationError) as exc_info:
            raise UserRoleCreationError(message)
        
        assert str(exc_info.value) == message
