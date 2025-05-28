"""
Test file for respond_invitation_use_case.py

This file contains unit tests for the respond invitation use case.
Tests cover all functions and edge cases with proper mocking.
"""

from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from datetime import datetime

# Import the functions to test
from use_cases.respond_invitation_use_case import (
    respond_invitation,
    _validate_invitation,
    _delete_invitation_notifications,
    _create_user_role_farm_association,
    _send_response_notification
)
from models.models import Invitations
from utils.constants import (
    STATE_ACTIVE,
    NOTIFICATION_TYPE_ACCEPTED
)


class TestRespondInvitationUseCase:
    """Test class for RespondInvitationUseCase"""
    
    def setup_method(self):
        """Setup method called before each test"""
        self.mock_db = Mock(spec=Session)
        self.mock_user = Mock()
        self.mock_user.user_id = 1
        self.mock_user.name = "Test User"
        
        # Sample invitation data
        self.sample_invitation = Mock(spec=Invitations)
        self.sample_invitation.invitation_id = 1
        self.sample_invitation.invited_user_id = 1
        self.sample_invitation.inviter_user_id = 2
        self.sample_invitation.farm_id = 10
        self.sample_invitation.suggested_role_id = 3
        self.sample_invitation.invitation_date = datetime.now()
    
    def teardown_method(self):
        """Teardown method called after each test"""
        pass

    # Tests for _validate_invitation function
    def test_validate_invitation_success(self):
        """Test successful invitation validation"""
        # Mock database query
        mock_query = self.mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = self.sample_invitation
        
        invitation, error = _validate_invitation(1, self.mock_user, self.mock_db)
        
        assert invitation == self.sample_invitation
        assert error is None
        self.mock_db.query.assert_called_once_with(Invitations)

    def test_validate_invitation_not_found(self):
        """Test invitation validation when invitation doesn't exist"""
        # Mock database query to return None
        mock_query = self.mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None
        
        invitation, error = _validate_invitation(1, self.mock_user, self.mock_db)
        
        assert invitation is None
        assert error is not None
        assert error.status_code == 404

    def test_validate_invitation_permission_denied(self):
        """Test invitation validation when user doesn't have permission"""
        # Set different user ID for permission test
        self.sample_invitation.invited_user_id = 999
        
        mock_query = self.mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = self.sample_invitation
        
        invitation, error = _validate_invitation(1, self.mock_user, self.mock_db)
        
        assert invitation is None
        assert error is not None
        assert error.status_code == 403

    # Tests for _delete_invitation_notifications function
    @patch('use_cases.respond_invitation_use_case.delete_notifications_by_invitation_id')
    def test_delete_invitation_notifications_success(self, mock_delete_notifications):
        """Test successful deletion of invitation notifications"""
        mock_delete_notifications.return_value = {"deleted_count": 2}
        
        # Should not raise any exception
        _delete_invitation_notifications(1)
        
        mock_delete_notifications.assert_called_once_with(1)

    @patch('use_cases.respond_invitation_use_case.delete_notifications_by_invitation_id')
    def test_delete_invitation_notifications_no_notifications(self, mock_delete_notifications):
        """Test deletion when no notifications found"""
        mock_delete_notifications.return_value = {"deleted_count": 0}
        
        # Should not raise any exception
        _delete_invitation_notifications(1)
        
        mock_delete_notifications.assert_called_once_with(1)

    @patch('use_cases.respond_invitation_use_case.delete_notifications_by_invitation_id')
    @patch('use_cases.respond_invitation_use_case.logger')
    def test_delete_invitation_notifications_exception(self, mock_logger, mock_delete_notifications):
        """Test deletion when an exception occurs"""
        mock_delete_notifications.side_effect = Exception("Connection error")
        
        # Should not raise any exception but log the error
        _delete_invitation_notifications(1)
        
        mock_logger.error.assert_called_once()

    # Tests for _create_user_role_farm_association function
    @patch('use_cases.respond_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.respond_invitation_use_case.create_user_role')
    @patch('use_cases.respond_invitation_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.respond_invitation_use_case.create_user_role_farm')
    def test_create_user_role_farm_association_success(self, mock_create_urf, mock_get_state, 
                                                      mock_create_user_role, mock_get_role_name):
        """Test successful creation of user-role-farm association"""
        # Setup mocks
        mock_get_role_name.return_value = "Farm Manager"
        mock_create_user_role.return_value = {"user_role_id": 123}
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_create_urf.return_value = {"status": "success"}
        
        result = _create_user_role_farm_association(1, 3, 10)
        
        assert result is None  # Success returns None
        mock_get_role_name.assert_called_once_with(3)
        mock_create_user_role.assert_called_once_with(1, "Farm Manager")
        mock_get_state.assert_called_once_with(STATE_ACTIVE)
        mock_create_urf.assert_called_once_with(123, 10, 1)

    @patch('use_cases.respond_invitation_use_case.get_role_name_by_id')
    def test_create_user_role_farm_association_invalid_role(self, mock_get_role_name):
        """Test creation with invalid role"""
        mock_get_role_name.return_value = None
        
        result = _create_user_role_farm_association(1, 999, 10)
        
        assert result is not None
        assert result.status_code == 400

    @patch('use_cases.respond_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.respond_invitation_use_case.create_user_role')
    def test_create_user_role_farm_association_user_role_creation_fails(self, mock_create_user_role, mock_get_role_name):
        """Test creation when user role creation fails"""
        mock_get_role_name.return_value = "Farm Manager"
        mock_create_user_role.return_value = {}  # No user_role_id
        
        result = _create_user_role_farm_association(1, 3, 10)
        
        assert result is not None
        assert result.status_code == 500

    @patch('use_cases.respond_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.respond_invitation_use_case.create_user_role')
    @patch('use_cases.respond_invitation_use_case.get_user_role_farm_state_by_name')
    def test_create_user_role_farm_association_state_not_found(self, mock_get_state, mock_create_user_role, mock_get_role_name):
        """Test creation when active state is not found"""
        mock_get_role_name.return_value = "Farm Manager"
        mock_create_user_role.return_value = {"user_role_id": 123}
        mock_get_state.return_value = None
        
        result = _create_user_role_farm_association(1, 3, 10)
        
        assert result is not None
        assert result.status_code == 500

    @patch('use_cases.respond_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.respond_invitation_use_case.create_user_role')
    @patch('use_cases.respond_invitation_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.respond_invitation_use_case.create_user_role_farm')
    def test_create_user_role_farm_association_urf_creation_fails(self, mock_create_urf, mock_get_state, 
                                                                 mock_create_user_role, mock_get_role_name):
        """Test creation when UserRoleFarm creation fails"""
        mock_get_role_name.return_value = "Farm Manager"
        mock_create_user_role.return_value = {"user_role_id": 123}
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_create_urf.return_value = {"status": "error"}
        
        result = _create_user_role_farm_association(1, 3, 10)
        
        assert result is not None
        assert result.status_code == 500

    @patch('use_cases.respond_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.respond_invitation_use_case.create_user_role')
    def test_create_user_role_farm_association_exception(self, mock_create_user_role, mock_get_role_name):
        """Test creation when an exception occurs"""
        mock_get_role_name.return_value = "Farm Manager"
        mock_create_user_role.side_effect = Exception("Database error")
        
        result = _create_user_role_farm_association(1, 3, 10)
        
        assert result is not None
        assert result.status_code == 500

    # Tests for _send_response_notification function
    @patch('use_cases.respond_invitation_use_case.get_notification_type_by_name')
    @patch('use_cases.respond_invitation_use_case.get_notification_state_by_name')
    @patch('use_cases.respond_invitation_use_case.get_farm_by_id')
    @patch('use_cases.respond_invitation_use_case.send_notification')
    def test_send_response_notification_success(self, mock_send_notification, mock_get_farm, 
                                               mock_get_state, mock_get_type):
        """Test successful notification sending"""
        # Setup mocks
        mock_farm = Mock()
        mock_farm.name = "Test Farm"
        mock_get_farm.return_value = mock_farm
        mock_get_type.return_value = {"notification_type_id": 1}
        mock_get_state.return_value = {"notification_state_id": 2}
        
        result = _send_response_notification("Test User", 10, 2, 1, 
                                           NOTIFICATION_TYPE_ACCEPTED, "aceptado")
        
        assert result is None  # Success returns None
        mock_send_notification.assert_called_once()

    @patch('use_cases.respond_invitation_use_case.get_notification_type_by_name')
    @patch('use_cases.respond_invitation_use_case.get_notification_state_by_name')
    @patch('use_cases.respond_invitation_use_case.get_farm_by_id')
    @patch('use_cases.respond_invitation_use_case.send_notification')
    def test_send_response_notification_farm_not_found(self, mock_send_notification, mock_get_farm, 
                                                       mock_get_state, mock_get_type):
        """Test notification sending when farm is not found"""
        mock_get_farm.return_value = None
        
        result = _send_response_notification("Test User", 999, 2, 1, 
                                           NOTIFICATION_TYPE_ACCEPTED, "aceptado")
        
        assert result is not None
        assert result.status_code == 404

    # Tests for respond_invitation function
    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    @patch('use_cases.respond_invitation_use_case._create_user_role_farm_association')
    @patch('use_cases.respond_invitation_use_case._send_response_notification')
    def test_respond_invitation_accept_success(self, mock_send_notification, mock_create_association,
                                             mock_delete_notifications, mock_validate):
        """Test successful invitation acceptance"""
        # Setup mocks
        mock_validate.return_value = (self.sample_invitation, None)
        mock_create_association.return_value = None
        mock_send_notification.return_value = None
        
        result = respond_invitation(1, "accept", self.mock_user, self.mock_db)
        
        assert result.status_code == 200
        mock_validate.assert_called_once_with(1, self.mock_user, self.mock_db)
        mock_delete_notifications.assert_called_once_with(1)
        mock_create_association.assert_called_once_with(1, 3, 10)
        self.mock_db.delete.assert_called_once_with(self.sample_invitation)
        self.mock_db.commit.assert_called_once()
        mock_send_notification.assert_called_once()

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    @patch('use_cases.respond_invitation_use_case._send_response_notification')
    def test_respond_invitation_reject_success(self, mock_send_notification, 
                                             mock_delete_notifications, mock_validate):
        """Test successful invitation rejection"""
        # Setup mocks
        mock_validate.return_value = (self.sample_invitation, None)
        mock_send_notification.return_value = None
        
        result = respond_invitation(1, "reject", self.mock_user, self.mock_db)
        
        assert result.status_code == 200
        mock_validate.assert_called_once_with(1, self.mock_user, self.mock_db)
        mock_delete_notifications.assert_called_once_with(1)
        self.mock_db.delete.assert_called_once_with(self.sample_invitation)
        self.mock_db.commit.assert_called_once()
        mock_send_notification.assert_called_once()

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    def test_respond_invitation_validation_error(self, mock_validate):
        """Test invitation response when validation fails"""
        mock_error_response = Mock()
        mock_error_response.status_code = 404
        mock_validate.return_value = (None, mock_error_response)
        
        result = respond_invitation(1, "accept", self.mock_user, self.mock_db)
        
        assert result == mock_error_response
        mock_validate.assert_called_once_with(1, self.mock_user, self.mock_db)

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    @patch('use_cases.respond_invitation_use_case._create_user_role_farm_association')
    def test_respond_invitation_accept_association_error(self, mock_create_association,
                                                        mock_delete_notifications, mock_validate):
        """Test invitation acceptance when association creation fails"""
        mock_validate.return_value = (self.sample_invitation, None)
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_create_association.return_value = mock_error_response
        
        result = respond_invitation(1, "accept", self.mock_user, self.mock_db)
        
        assert result == mock_error_response
        mock_create_association.assert_called_once()

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    @patch('use_cases.respond_invitation_use_case._create_user_role_farm_association')
    @patch('use_cases.respond_invitation_use_case._send_response_notification')
    def test_respond_invitation_accept_notification_error(self, mock_send_notification, mock_create_association,
                                                         mock_delete_notifications, mock_validate):
        """Test invitation acceptance when notification sending fails"""
        mock_validate.return_value = (self.sample_invitation, None)
        mock_create_association.return_value = None
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_send_notification.return_value = mock_error_response
        
        result = respond_invitation(1, "accept", self.mock_user, self.mock_db)
        
        assert result == mock_error_response
        mock_send_notification.assert_called_once()

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    @patch('use_cases.respond_invitation_use_case._send_response_notification')
    def test_respond_invitation_reject_notification_error(self, mock_send_notification,
                                                         mock_delete_notifications, mock_validate):
        """Test invitation rejection when notification sending fails"""
        mock_validate.return_value = (self.sample_invitation, None)
        mock_error_response = Mock()
        mock_error_response.status_code = 500
        mock_send_notification.return_value = mock_error_response
        
        result = respond_invitation(1, "reject", self.mock_user, self.mock_db)
        
        assert result == mock_error_response
        mock_send_notification.assert_called_once()

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    def test_respond_invitation_invalid_action(self, mock_validate):
        """Test invitation response with invalid action"""
        # Setup validation to fail first (which is what actually happens)
        mock_error_response = Mock()
        mock_error_response.status_code = 403
        mock_validate.return_value = (None, mock_error_response)
        
        result = respond_invitation(1, "invalid_action", self.mock_user, self.mock_db)
        
        assert result.status_code == 403

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    def test_respond_invitation_truly_invalid_action(self, mock_delete_notifications, mock_validate):
        """Test invitation response with invalid action when validation succeeds"""
        # Setup validation to succeed
        mock_validate.return_value = (self.sample_invitation, None)
        
        result = respond_invitation(1, "invalid_action", self.mock_user, self.mock_db)
        
        assert result.status_code == 400

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    @patch('use_cases.respond_invitation_use_case._create_user_role_farm_association')
    @patch('use_cases.respond_invitation_use_case._send_response_notification')
    def test_respond_invitation_empty_action(self, mock_send_notification, mock_create_association,
                                           mock_delete_notifications, mock_validate):
        """Test invitation response with empty action"""
        # Setup validation to fail first (which is what actually happens)
        mock_error_response = Mock()
        mock_error_response.status_code = 403
        mock_validate.return_value = (None, mock_error_response)
        
        result = respond_invitation(1, "", self.mock_user, self.mock_db)
        assert result.status_code == 403

    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    @patch('use_cases.respond_invitation_use_case._create_user_role_farm_association')
    @patch('use_cases.respond_invitation_use_case._send_response_notification')
    def test_respond_invitation_case_insensitive_actions(self, mock_send_notification, mock_create_association,
                                                        mock_delete_notifications, mock_validate):
        """Test that actions are case insensitive"""
        mock_validate.return_value = (self.sample_invitation, None)
        mock_create_association.return_value = None
        mock_send_notification.return_value = None
        
        # Test uppercase ACCEPT
        result = respond_invitation(1, "ACCEPT", self.mock_user, self.mock_db)
        assert result.status_code == 200
        
        # Reset mocks
        self.mock_db.reset_mock()
        mock_validate.return_value = (self.sample_invitation, None)
        mock_send_notification.return_value = None
        
        # Test mixed case Reject
        result = respond_invitation(1, "Reject", self.mock_user, self.mock_db)
        assert result.status_code == 200

    # Additional edge case tests
    @patch('use_cases.respond_invitation_use_case._validate_invitation')
    @patch('use_cases.respond_invitation_use_case._delete_invitation_notifications')
    @patch('use_cases.respond_invitation_use_case._create_user_role_farm_association')
    @patch('use_cases.respond_invitation_use_case._send_response_notification')
    def test_respond_invitation_whitespace_action(self, mock_send_notification, mock_create_association,
                                                 mock_delete_notifications, mock_validate):
        """Test invitation response with whitespace in action"""
        mock_validate.return_value = (self.sample_invitation, None)
        mock_create_association.return_value = None
        mock_send_notification.return_value = None
        
        # Test action with whitespace
        result = respond_invitation(1, "  accept  ", self.mock_user, self.mock_db)
        assert result.status_code == 400  # Should fail because of leading/trailing spaces

    @patch('use_cases.respond_invitation_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.respond_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.respond_invitation_use_case.create_user_role')
    def test_create_user_role_farm_association_state_missing_id(self, mock_create_user_role, 
                                                               mock_get_role_name, mock_get_state):
        """Test creation when state is found but missing user_role_farm_state_id"""
        mock_get_role_name.return_value = "Farm Manager"
        mock_create_user_role.return_value = {"user_role_id": 123}
        mock_get_state.return_value = {"name": "Activo"}  # Missing user_role_farm_state_id
        
        result = _create_user_role_farm_association(1, 3, 10)
        
        assert result is not None
        assert result.status_code == 500

    @patch('use_cases.respond_invitation_use_case.get_notification_type_by_name')
    @patch('use_cases.respond_invitation_use_case.get_notification_state_by_name')
    @patch('use_cases.respond_invitation_use_case.get_farm_by_id')
    @patch('use_cases.respond_invitation_use_case.send_notification')
    def test_send_response_notification_with_none_values(self, mock_send_notification, mock_get_farm, 
                                                        mock_get_state, mock_get_type):
        """Test notification sending when some services return None"""
        # Setup mocks
        mock_farm = Mock()
        mock_farm.name = "Test Farm"
        mock_get_farm.return_value = mock_farm
        mock_get_type.return_value = None  # Service returns None
        mock_get_state.return_value = None  # Service returns None
        
        result = _send_response_notification("Test User", 10, 2, 1, 
                                           NOTIFICATION_TYPE_ACCEPTED, "aceptado")
        
        assert result is None  # Should still work
        # Verify send_notification was called with None values
        call_args = mock_send_notification.call_args[1]
        assert call_args['notification_type_id'] is None
        assert call_args['notification_state_id'] is None 