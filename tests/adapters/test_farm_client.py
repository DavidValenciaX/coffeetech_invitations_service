"""
Test file for farm_client.py

This file contains comprehensive unit tests for the farm client adapter.
Tests cover all functions, edge cases, and error scenarios including
HTTP client interactions, timeouts, and API responses.
"""

from unittest.mock import Mock, patch
import httpx
from domain.schemas import FarmDetailResponse, UserRoleFarmResponse
from adapters.farm_client import (
    get_farm_by_id,
    get_user_role_farm,
    create_user_role_farm,
    get_user_role_farm_state_by_name
)


class TestFarmClient:
    """Test class for farm client adapter functions"""
    
    def setup_method(self):
        """Setup method called before each test"""
        # Mock farm response data
        self.farm_data = {
            "farm_id": 1,
            "name": "Test Farm",
            "area": 100.5,
            "area_unit_id": 1,
            "area_unit": "hectares",
            "farm_state_id": 1,
            "farm_state": "Active"
        }
        
        # Mock user role farm response data
        self.urf_data = {
            "user_role_farm_id": 1,
            "user_role_id": 2,
            "farm_id": 1,
            "user_role_farm_state_id": 1,
            "user_role_farm_state": "Activo"
        }
        
        # Mock state response data
        self.state_data = {
            "user_role_farm_state_id": 1,
            "state_name": "Activo"
        }
        
        # Mock create response data
        self.create_response = {
            "status": "success",
            "message": "UserRoleFarm created successfully",
            "user_role_farm_id": 1
        }
        
    def teardown_method(self):
        """Teardown method called after each test"""
        pass


class TestGetFarmById(TestFarmClient):
    """Tests for get_farm_by_id function"""
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_success(self, mock_time, mock_client):
        """Test successful farm retrieval"""
        # Arrange
        farm_id = 1
        mock_time.side_effect = [0.0, 1.5]  # Start and end times
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.farm_data
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is not None
        assert isinstance(result, FarmDetailResponse)
        assert result.farm_id == 1
        assert result.name == "Test Farm"
        assert abs(result.area - 100.5) < 0.001  # Use approximate comparison for float
        mock_client_instance.get.assert_called_once_with(
            "http://localhost:8002/farms-service/get-farm/1"
        )
        
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    @patch('adapters.farm_client.logger')
    def test_get_farm_by_id_timeout(self, mock_logger, mock_time, mock_client):
        """Test timeout scenario"""
        # Arrange
        farm_id = 1
        mock_time.side_effect = [0.0, 60.5]  # Simulate timeout duration
        
        mock_client_instance = Mock()
        mock_client_instance.get.side_effect = httpx.TimeoutException("Request timeout")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "Timeout" in error_call_args
        assert f"finca {farm_id}" in error_call_args
        
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    @patch('adapters.farm_client.logger')
    def test_get_farm_by_id_http_error(self, mock_logger, mock_time, mock_client):
        """Test HTTP error scenario"""
        # Arrange
        farm_id = 1
        mock_time.side_effect = [0.0, 0.5, 0.5]  # Provide extra value for duration calculation
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None
        mock_logger.error.assert_called_once()
        
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    @patch('adapters.farm_client.logger')
    def test_get_farm_by_id_generic_exception(self, mock_logger, mock_time, mock_client):
        """Test generic exception handling"""
        # Arrange
        farm_id = 1
        mock_time.side_effect = [0.0, 0.2]
        
        mock_client_instance = Mock()
        mock_client_instance.get.side_effect = Exception("Connection error")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "Exception" in error_call_args
        assert "Connection error" in error_call_args
        
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    @patch('adapters.farm_client.logger')
    def test_get_farm_by_id_invalid_json(self, mock_logger, mock_time, mock_client):
        """Test invalid JSON response handling"""
        # Arrange
        farm_id = 1
        mock_time.side_effect = [0.0, 0.3, 0.3]  # Provide extra value for duration calculation
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is None
        mock_logger.error.assert_called_once()


class TestGetUserRoleFarm(TestFarmClient):
    """Tests for get_user_role_farm function"""
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_success(self, mock_client):
        """Test successful user role farm retrieval"""
        # Arrange
        user_id = 1
        farm_id = 1
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.urf_data
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert result is not None
        assert isinstance(result, UserRoleFarmResponse)
        assert result.user_role_farm_id == 1
        assert result.user_role_id == 2
        assert result.farm_id == 1
        mock_client_instance.get.assert_called_once_with(
            "http://localhost:8002/farms-service/get-user-role-farm/1/1"
        )
        
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_error_status(self, mock_client):
        """Test error status in response"""
        # Arrange
        user_id = 1
        farm_id = 1
        error_response = {"status": "error", "message": "Not found"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert result is None
        
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.logger')
    def test_get_user_role_farm_exception(self, mock_logger, mock_client):
        """Test exception handling"""
        # Arrange
        user_id = 1
        farm_id = 1
        
        mock_client_instance = Mock()
        mock_client_instance.get.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=Mock(), response=Mock()
        )
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_user_role_farm(user_id, farm_id)
        
        # Assert
        assert result is None
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "Error al consultar user_role_farm" in error_call_args


class TestCreateUserRoleFarm(TestFarmClient):
    """Tests for create_user_role_farm function"""
    
    @patch('adapters.farm_client.httpx.Client')
    def test_create_user_role_farm_success(self, mock_client):
        """Test successful user role farm creation"""
        # Arrange
        user_role_id = 2
        farm_id = 1
        user_role_farm_state_id = 1
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = self.create_response
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = create_user_role_farm(user_role_id, farm_id, user_role_farm_state_id)
        
        # Assert
        assert result is not None
        assert result["status"] == "success"
        assert result["user_role_farm_id"] == 1
        
        expected_payload = {
            "user_role_id": user_role_id,
            "farm_id": farm_id,
            "user_role_farm_state_id": user_role_farm_state_id
        }
        mock_client_instance.post.assert_called_once_with(
            "http://localhost:8002/farms-service/create-user-role-farm",
            json=expected_payload
        )
        
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.logger')
    def test_create_user_role_farm_http_error(self, mock_logger, mock_client):
        """Test HTTP error during creation"""
        # Arrange
        user_role_id = 2
        farm_id = 1
        user_role_farm_state_id = 1
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=Mock(), response=mock_response
        )
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = create_user_role_farm(user_role_id, farm_id, user_role_farm_state_id)
        
        # Assert
        assert result is not None
        assert result["status"] == "error"
        assert "Error al crear user_role_farm" in result["message"]
        mock_logger.error.assert_called_once()
        
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.logger')
    def test_create_user_role_farm_connection_error(self, mock_logger, mock_client):
        """Test connection error during creation"""
        # Arrange
        user_role_id = 2
        farm_id = 1
        user_role_farm_state_id = 1
        
        mock_client_instance = Mock()
        mock_client_instance.post.side_effect = httpx.ConnectError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = create_user_role_farm(user_role_id, farm_id, user_role_farm_state_id)
        
        # Assert
        assert result is not None
        assert result["status"] == "error"
        assert "Connection failed" in result["message"]
        mock_logger.error.assert_called_once()


class TestGetUserRoleFarmStateByName(TestFarmClient):
    """Tests for get_user_role_farm_state_by_name function"""
    
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_state_by_name_success(self, mock_client):
        """Test successful state retrieval by name"""
        # Arrange
        state_name = "Activo"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.state_data
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result is not None
        assert result["user_role_farm_state_id"] == 1
        assert result["state_name"] == "Activo"
        mock_client_instance.get.assert_called_once_with(
            "http://localhost:8002/farms-service/get-user-role-farm-state/Activo"
        )
        
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_state_by_name_error_status(self, mock_client):
        """Test error status in response"""
        # Arrange
        state_name = "NonExistent"
        error_response = {"status": "error", "message": "State not found"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result is None
        
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.logger')
    def test_get_user_role_farm_state_by_name_exception(self, mock_logger, mock_client):
        """Test exception handling"""
        # Arrange
        state_name = "Activo"
        
        mock_client_instance = Mock()
        mock_client_instance.get.side_effect = httpx.RequestError("Network error")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result is None
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "Error al consultar user_role_farm_state" in error_call_args
        
    @patch('adapters.farm_client.httpx.Client')
    def test_get_user_role_farm_state_by_name_with_special_characters(self, mock_client):
        """Test state name with special characters"""
        # Arrange
        state_name = "Activo con espacios"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "user_role_farm_state_id": 2,
            "state_name": state_name
        }
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_user_role_farm_state_by_name(state_name)
        
        # Assert
        assert result is not None
        assert result["state_name"] == state_name
        mock_client_instance.get.assert_called_once_with(
            "http://localhost:8002/farms-service/get-user-role-farm-state/Activo con espacios"
        )


class TestFarmClientIntegration(TestFarmClient):
    """Integration tests for farm client functions"""
    
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_timeout_logging(self, mock_time, mock_client):
        """Test that timeout logging includes duration"""
        # Arrange
        farm_id = 1
        mock_time.side_effect = [0.0, 60.1234]  # Start and timeout end
        
        mock_client_instance = Mock()
        mock_client_instance.get.side_effect = httpx.TimeoutException("Timeout occurred")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        with patch('adapters.farm_client.logger') as mock_logger:
            # Act
            result = get_farm_by_id(farm_id)
            
            # Assert
            assert result is None
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "60.1234 segundos" in error_message
            
    @patch('adapters.farm_client.httpx.Client')
    @patch('adapters.farm_client.time.monotonic')
    def test_get_farm_by_id_success_logging(self, mock_time, mock_client):
        """Test that success logging includes duration and status code"""
        # Arrange
        farm_id = 1
        mock_time.side_effect = [0.0, 1.5678]  # Start and success end
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.farm_data
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        with patch('adapters.farm_client.logger') as mock_logger:
            # Act
            result = get_farm_by_id(farm_id)
            
            # Assert
            assert result is not None
            # Should have info calls for start and completion
            assert mock_logger.info.call_count == 2
            completion_call = mock_logger.info.call_args_list[1][0][0]
            assert "1.5678 segundos" in completion_call
            assert "estado 200" in completion_call


class TestFarmClientEnvironmentVariables(TestFarmClient):
    """Tests for environment variable handling"""
    
    @patch('adapters.farm_client.FARMS_SERVICE_URL', 'http://custom-farms-service:9000')
    @patch('adapters.farm_client.httpx.Client')
    def test_custom_farms_service_url(self, mock_client):
        """Test using custom FARMS_SERVICE_URL from environment"""
        # Arrange
        farm_id = 1
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.farm_data
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_farm_by_id(farm_id)
        
        # Assert
        assert result is not None
        expected_url = "http://custom-farms-service:9000/farms-service/get-farm/1"
        mock_client_instance.get.assert_called_once_with(expected_url)
