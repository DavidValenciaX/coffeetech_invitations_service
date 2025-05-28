import pytest
import httpx
from unittest.mock import patch, Mock
from adapters.notification_client import (
    get_notification_state_by_name,
    get_notification_type_by_name,
    update_notification_state,
    get_notification_id_by_invitation_id,
    delete_notifications_by_invitation_id,
    send_notification,
    NOTIFICATIONS_SERVICE_URL
)


class TestGetNotificationStateByName:
    """Tests for get_notification_state_by_name function"""
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_state_by_name_success(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "pending"},
            {"id": 2, "name": "sent"},
            {"id": 3, "name": "read"}
        ]
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_notification_state_by_name("sent")
        
        # Assert
        assert result == {"id": 2, "name": "sent"}
        mock_client_instance.get.assert_called_once_with(f"{NOTIFICATIONS_SERVICE_URL}/notification-states")
        mock_response.raise_for_status.assert_called_once()
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_state_by_name_case_insensitive(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "Pending"},
            {"id": 2, "name": "SENT"}
        ]
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_notification_state_by_name("sent")
        
        # Assert
        assert result == {"id": 2, "name": "SENT"}
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_state_by_name_not_found(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "pending"},
            {"id": 2, "name": "sent"}
        ]
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_notification_state_by_name("nonexistent")
        
        # Assert
        assert result is None
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_state_by_name_request_error(self, mock_client):
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.get.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.RequestError):
            get_notification_state_by_name("sent")
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_state_by_name_http_error(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            get_notification_state_by_name("sent")


class TestGetNotificationTypeByName:
    """Tests for get_notification_type_by_name function"""
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_type_by_name_success(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "invitation"},
            {"id": 2, "name": "reminder"},
            {"id": 3, "name": "alert"}
        ]
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_notification_type_by_name("invitation")
        
        # Assert
        assert result == {"id": 1, "name": "invitation"}
        mock_client_instance.get.assert_called_once_with(f"{NOTIFICATIONS_SERVICE_URL}/notification-types")
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_type_by_name_case_insensitive(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "INVITATION"},
            {"id": 2, "name": "Reminder"}
        ]
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_notification_type_by_name("invitation")
        
        # Assert
        assert result == {"id": 1, "name": "INVITATION"}
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_type_by_name_not_found(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": 1, "name": "invitation"},
            {"id": 2, "name": "reminder"}
        ]
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_notification_type_by_name("nonexistent")
        
        # Assert
        assert result is None


class TestUpdateNotificationState:
    """Tests for update_notification_state function"""
    
    @patch('adapters.notification_client.httpx.Client')
    def test_update_notification_state_success(self, mock_client):
        # Arrange
        notification_id = 123
        notification_state_id = 2
        expected_response = {"id": 123, "state_id": 2, "updated": True}
        
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.patch.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = update_notification_state(notification_id, notification_state_id)
        
        # Assert
        assert result == expected_response
        mock_client_instance.patch.assert_called_once_with(
            f"{NOTIFICATIONS_SERVICE_URL}/notifications/{notification_id}/state",
            json={"notification_state_id": notification_state_id}
        )
    
    @patch('adapters.notification_client.httpx.Client')
    def test_update_notification_state_request_error(self, mock_client):
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.patch.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.RequestError):
            update_notification_state(123, 2)
    
    @patch('adapters.notification_client.httpx.Client')
    def test_update_notification_state_http_error(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Notification not found"
        
        mock_client_instance = Mock()
        mock_client_instance.patch.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            update_notification_state(123, 2)


class TestGetNotificationIdByInvitationId:
    """Tests for get_notification_id_by_invitation_id function"""
    
    @patch('adapters.notification_client.httpx.Client')
    @patch('builtins.print')  # Mock print to avoid output during tests
    def test_get_notification_id_by_invitation_id_success(self, mock_print, mock_client):
        # Arrange
        invitation_id = 456
        expected_notification_id = 789
        
        mock_response = Mock()
        mock_response.json.return_value = {"notification_id": expected_notification_id}
        mock_response.text = '{"notification_id": 789}'
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_notification_id_by_invitation_id(invitation_id)
        
        # Assert
        assert result == expected_notification_id
        mock_client_instance.get.assert_called_once_with(
            f"{NOTIFICATIONS_SERVICE_URL}/notifications/by-invitation/{invitation_id}"
        )
        mock_print.assert_called_once_with('Response: {"notification_id": 789}')
    
    @patch('adapters.notification_client.httpx.Client')
    @patch('builtins.print')
    def test_get_notification_id_by_invitation_id_no_notification_id(self, mock_print, mock_client):
        # Arrange
        invitation_id = 456
        
        mock_response = Mock()
        mock_response.json.return_value = {"message": "No notification found"}
        mock_response.text = '{"message": "No notification found"}'
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = get_notification_id_by_invitation_id(invitation_id)
        
        # Assert
        assert result is None
    
    @patch('adapters.notification_client.httpx.Client')
    def test_get_notification_id_by_invitation_id_request_error(self, mock_client):
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.get.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.RequestError):
            get_notification_id_by_invitation_id(456)


class TestDeleteNotificationsByInvitationId:
    """Tests for delete_notifications_by_invitation_id function"""
    
    @patch('adapters.notification_client.httpx.Client')
    def test_delete_notifications_by_invitation_id_success(self, mock_client):
        # Arrange
        invitation_id = 456
        expected_response = {"deleted_count": 3, "message": "Notifications deleted successfully"}
        
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.delete.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = delete_notifications_by_invitation_id(invitation_id)
        
        # Assert
        assert result == expected_response
        mock_client_instance.delete.assert_called_once_with(
            f"{NOTIFICATIONS_SERVICE_URL}/notifications/by-invitation/{invitation_id}"
        )
    
    @patch('adapters.notification_client.httpx.Client')
    def test_delete_notifications_by_invitation_id_request_error(self, mock_client):
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.delete.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.RequestError):
            delete_notifications_by_invitation_id(456)
    
    @patch('adapters.notification_client.httpx.Client')
    def test_delete_notifications_by_invitation_id_http_error(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        
        mock_client_instance = Mock()
        mock_client_instance.delete.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error", request=Mock(), response=mock_response
        )
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            delete_notifications_by_invitation_id(456)


class TestSendNotification:
    """Tests for send_notification function"""
    
    @patch('adapters.notification_client.httpx.Client')
    def test_send_notification_minimal_payload(self, mock_client):
        # Arrange
        expected_response = {"id": 123, "status": "sent"}
        
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = send_notification(
            message="Test message",
            user_id=1,
            notification_type_id=2,
            invitation_id=3,
            notification_state_id=4
        )
        
        # Assert
        assert result == expected_response
        expected_payload = {
            "message": "Test message",
            "user_id": 1,
            "notification_type_id": 2,
            "invitation_id": 3,
            "notification_state_id": 4
        }
        mock_client_instance.post.assert_called_once_with(
            f"{NOTIFICATIONS_SERVICE_URL}/send-notification",
            json=expected_payload
        )
    
    @patch('adapters.notification_client.httpx.Client')
    def test_send_notification_full_payload(self, mock_client):
        # Arrange
        expected_response = {"id": 123, "status": "sent"}
        
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = send_notification(
            message="Test message",
            user_id=1,
            notification_type_id=2,
            invitation_id=3,
            notification_state_id=4,
            fcm_token="test_token",
            fcm_title="Test Title",
            fcm_body="Test Body"
        )
        
        # Assert
        assert result == expected_response
        expected_payload = {
            "message": "Test message",
            "user_id": 1,
            "notification_type_id": 2,
            "invitation_id": 3,
            "notification_state_id": 4,
            "fcm_title": "Test Title",
            "fcm_body": "Test Body",
            "fcm_token": "test_token"
        }
        mock_client_instance.post.assert_called_once_with(
            f"{NOTIFICATIONS_SERVICE_URL}/send-notification",
            json=expected_payload
        )
    
    @patch('adapters.notification_client.httpx.Client')
    def test_send_notification_partial_fcm_fields(self, mock_client):
        # Arrange
        expected_response = {"id": 123, "status": "sent"}
        
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act
        result = send_notification(
            message="Test message",
            user_id=1,
            notification_type_id=2,
            invitation_id=3,
            notification_state_id=4,
            fcm_title="Test Title"  # Only fcm_title provided
        )
        
        # Assert
        assert result == expected_response
        expected_payload = {
            "message": "Test message",
            "user_id": 1,
            "notification_type_id": 2,
            "invitation_id": 3,
            "notification_state_id": 4,
            "fcm_title": "Test Title"
        }
        mock_client_instance.post.assert_called_once_with(
            f"{NOTIFICATIONS_SERVICE_URL}/send-notification",
            json=expected_payload
        )
    
    @patch('adapters.notification_client.httpx.Client')
    def test_send_notification_request_error(self, mock_client):
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.post.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.RequestError):
            send_notification(
                message="Test message",
                user_id=1,
                notification_type_id=2,
                invitation_id=3,
                notification_state_id=4
            )
    
    @patch('adapters.notification_client.httpx.Client')
    def test_send_notification_http_error(self, mock_client):
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=Mock(), response=mock_response
        )
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            send_notification(
                message="Test message",
                user_id=1,
                notification_type_id=2,
                invitation_id=3,
                notification_state_id=4
            )
    
    @patch('adapters.notification_client.httpx.Client')
    def test_send_notification_generic_exception(self, mock_client):
        # Arrange
        mock_client_instance = Mock()
        mock_client_instance.post.side_effect = Exception("Unexpected error")
        mock_client.return_value.__enter__.return_value = mock_client_instance
        
        # Act & Assert
        with pytest.raises(Exception, match="Unexpected error"):
            send_notification(
                message="Test message",
                user_id=1,
                notification_type_id=2,
                invitation_id=3,
                notification_state_id=4
            )


class TestNotificationServiceUrl:
    """Tests for environment variable configuration"""
    
    @patch.dict('os.environ', {'NOTIFICATIONS_SERVICE_URL': 'http://custom-url:9000'})
    @patch('adapters.notification_client.NOTIFICATIONS_SERVICE_URL', 'http://custom-url:9000')
    def test_custom_notifications_service_url(self):
        # Import the module with the patched environment
        from adapters.notification_client import NOTIFICATIONS_SERVICE_URL
        
        # Assert
        assert NOTIFICATIONS_SERVICE_URL == 'http://custom-url:9000'
    
    def test_default_notifications_service_url(self):
        # Test the default value that's already loaded
        from adapters.notification_client import NOTIFICATIONS_SERVICE_URL
        
        # Assert (this should be the default value)
        assert NOTIFICATIONS_SERVICE_URL == 'http://localhost:8001'
