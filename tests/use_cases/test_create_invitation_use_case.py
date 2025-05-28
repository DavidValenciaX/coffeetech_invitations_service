"""
Test file for create_invitation_use_case.py

This file contains comprehensive unit tests for the create invitation use case.
Tests cover all functions, edge cases, and error scenarios.
"""

from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi.responses import ORJSONResponse

from use_cases.create_invitation_use_case import (
    create_invitation,
    _validate_farm_and_user_access,
    _validate_role_permissions,
    _validate_invited_user,
    _handle_invitation_creation_or_update,
    _send_invitation_notification
)
from domain.schemas import InvitationCreate, UserResponse, FarmDetailResponse, UserRoleFarmResponse
from utils.constants import (
    ROLE_ADMIN_FARM,
    ROLE_OPERATOR_FARM
)


class TestCreateInvitationUseCase:
    """Test class for CreateInvitationUseCase"""
    
    def setup_method(self):
        """Setup method called before each test"""
        # Mock invitation data
        self.invitation_data = InvitationCreate(
            email="invited@test.com",
            suggested_role_id=2,
            farm_id=1
        )
        
        # Mock user (inviter)
        self.user = UserResponse(
            user_id=1,
            name="Test User",
            email="inviter@test.com"
        )
        
        # Mock invited user
        self.invited_user = UserResponse(
            user_id=2,
            name="Invited User",
            email="invited@test.com"
        )
        
        # Mock farm
        self.farm = FarmDetailResponse(
            farm_id=1,
            name="Test Farm",
            area=100.0,
            area_unit_id=1,
            area_unit="hectares",
            farm_state_id=1,
            farm_state="Active"
        )
        
        # Mock user role farm
        self.urf = UserRoleFarmResponse(
            user_role_farm_id=1,
            user_role_id=1,
            farm_id=1,
            user_role_farm_state_id=1,
            user_role_farm_state="Activo"
        )
        
        # Mock database session
        self.db = Mock(spec=Session)
        
    def teardown_method(self):
        """Teardown method called after each test"""
        pass

    # Tests for _validate_farm_and_user_access function
    @patch('use_cases.create_invitation_use_case.get_farm_by_id')
    @patch('use_cases.create_invitation_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_invitation_use_case.get_user_role_farm')
    def test_validate_farm_and_user_access_success(self, mock_get_urf, mock_get_state, mock_get_farm):
        """Test successful farm and user access validation"""
        # Arrange
        mock_get_farm.return_value = self.farm
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_get_urf.return_value = self.urf
        
        # Act
        result, error = _validate_farm_and_user_access(self.invitation_data, self.user)
        
        # Assert
        assert error is None
        assert result is not None
        assert result["farm"] == self.farm
        assert result["urf"] == self.urf
        assert result["urf_active_state_id"] == 1
        
    @patch('use_cases.create_invitation_use_case.get_farm_by_id')
    def test_validate_farm_and_user_access_farm_not_found(self, mock_get_farm):
        """Test farm not found scenario"""
        # Arrange
        mock_get_farm.return_value = None
        
        # Act
        result, error = _validate_farm_and_user_access(self.invitation_data, self.user)
        
        # Assert
        assert result is None
        assert error is not None
        assert isinstance(error, ORJSONResponse)
        assert error.status_code == 404
        
    @patch('use_cases.create_invitation_use_case.get_farm_by_id')
    @patch('use_cases.create_invitation_use_case.get_user_role_farm_state_by_name')
    def test_validate_farm_and_user_access_state_not_found(self, mock_get_state, mock_get_farm):
        """Test when active state is not found"""
        # Arrange
        mock_get_farm.return_value = self.farm
        mock_get_state.return_value = None
        
        # Act
        result, error = _validate_farm_and_user_access(self.invitation_data, self.user)
        
        # Assert
        assert result is None
        assert error is not None
        assert error.status_code == 500
        
    @patch('use_cases.create_invitation_use_case.get_farm_by_id')
    @patch('use_cases.create_invitation_use_case.get_user_role_farm_state_by_name')
    @patch('use_cases.create_invitation_use_case.get_user_role_farm')
    def test_validate_farm_and_user_access_no_permission(self, mock_get_urf, mock_get_state, mock_get_farm):
        """Test when user has no access to farm"""
        # Arrange
        mock_get_farm.return_value = self.farm
        mock_get_state.return_value = {"user_role_farm_state_id": 1}
        mock_get_urf.return_value = None
        
        # Act
        result, error = _validate_farm_and_user_access(self.invitation_data, self.user)
        
        # Assert
        assert result is None
        assert error is not None
        assert error.status_code == 403

    # Tests for _validate_role_permissions function
    @patch('use_cases.create_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.create_invitation_use_case.get_role_permissions_for_user_role')
    def test_validate_role_permissions_admin_success(self, mock_get_permissions, mock_get_role):
        """Test successful admin role permission validation"""
        # Arrange
        mock_get_role.return_value = ROLE_ADMIN_FARM
        mock_get_permissions.return_value = ["add_administrator_farm", "other_permission"]
        
        # Act
        result, error = _validate_role_permissions(self.invitation_data, self.urf)
        
        # Assert
        assert error is None
        assert result == ROLE_ADMIN_FARM
        
    @patch('use_cases.create_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.create_invitation_use_case.get_role_permissions_for_user_role')
    def test_validate_role_permissions_operator_success(self, mock_get_permissions, mock_get_role):
        """Test successful operator role permission validation"""
        # Arrange
        mock_get_role.return_value = ROLE_OPERATOR_FARM
        mock_get_permissions.return_value = ["add_operator_farm", "other_permission"]
        
        # Act
        result, error = _validate_role_permissions(self.invitation_data, self.urf)
        
        # Assert
        assert error is None
        assert result == ROLE_OPERATOR_FARM
        
    @patch('use_cases.create_invitation_use_case.get_role_name_by_id')
    def test_validate_role_permissions_invalid_role(self, mock_get_role):
        """Test invalid role scenario"""
        # Arrange
        mock_get_role.return_value = None
        
        # Act
        result, error = _validate_role_permissions(self.invitation_data, self.urf)
        
        # Assert
        assert result is None
        assert error is not None
        assert error.status_code == 400
        
    @patch('use_cases.create_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.create_invitation_use_case.get_role_permissions_for_user_role')
    def test_validate_role_permissions_no_admin_permission(self, mock_get_permissions, mock_get_role):
        """Test when user lacks admin permission"""
        # Arrange
        mock_get_role.return_value = ROLE_ADMIN_FARM
        mock_get_permissions.return_value = ["other_permission"]
        
        # Act
        result, error = _validate_role_permissions(self.invitation_data, self.urf)
        
        # Assert
        assert result is None
        assert error is not None
        assert error.status_code == 403
        
    @patch('use_cases.create_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.create_invitation_use_case.get_role_permissions_for_user_role')
    def test_validate_role_permissions_no_operator_permission(self, mock_get_permissions, mock_get_role):
        """Test when user lacks operator permission"""
        # Arrange
        mock_get_role.return_value = ROLE_OPERATOR_FARM
        mock_get_permissions.return_value = ["other_permission"]
        
        # Act
        result, error = _validate_role_permissions(self.invitation_data, self.urf)
        
        # Assert
        assert result is None
        assert error is not None
        assert error.status_code == 403
        
    @patch('use_cases.create_invitation_use_case.get_role_name_by_id')
    @patch('use_cases.create_invitation_use_case.get_role_permissions_for_user_role')
    def test_validate_role_permissions_invalid_role_type(self, mock_get_permissions, mock_get_role):
        """Test when role is not admin or operator"""
        # Arrange
        mock_get_role.return_value = "Invalid Role"
        mock_get_permissions.return_value = ["some_permission"]
        
        # Act
        result, error = _validate_role_permissions(self.invitation_data, self.urf)
        
        # Assert
        assert result is None
        assert error is not None
        assert error.status_code == 403

    # Tests for _validate_invited_user function
    @patch('use_cases.create_invitation_use_case.user_verification_by_email')
    @patch('use_cases.create_invitation_use_case.get_user_role_farm')
    def test_validate_invited_user_success(self, mock_get_urf, mock_verify_user):
        """Test successful invited user validation"""
        # Arrange
        mock_verify_user.return_value = self.invited_user
        mock_get_urf.return_value = None  # User not associated with farm
        
        # Act
        result, error = _validate_invited_user(self.invitation_data, 1)
        
        # Assert
        assert error is None
        assert result == self.invited_user
        
    @patch('use_cases.create_invitation_use_case.user_verification_by_email')
    def test_validate_invited_user_not_found(self, mock_verify_user):
        """Test when invited user is not found"""
        # Arrange
        mock_verify_user.return_value = None
        
        # Act
        result, error = _validate_invited_user(self.invitation_data, 1)
        
        # Assert
        assert result is None
        assert error is not None
        assert error.status_code == 404
        
    @patch('use_cases.create_invitation_use_case.user_verification_by_email')
    @patch('use_cases.create_invitation_use_case.get_user_role_farm')
    def test_validate_invited_user_already_associated(self, mock_get_urf, mock_verify_user):
        """Test when user is already associated with farm"""
        # Arrange
        mock_verify_user.return_value = self.invited_user
        mock_urf = Mock()
        mock_urf.user_role_farm_state_id = 1
        mock_get_urf.return_value = mock_urf
        
        # Act
        result, error = _validate_invited_user(self.invitation_data, 1)
        
        # Assert
        assert result is None
        assert error is not None
        assert error.status_code == 400

    # Tests for _handle_invitation_creation_or_update function
    @patch('use_cases.create_invitation_use_case.delete_notifications_by_invitation_id')
    @patch('use_cases.create_invitation_use_case.datetime')
    def test_handle_invitation_update_existing(self, mock_datetime, mock_delete_notifications):
        """Test updating existing invitation"""
        # Arrange
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        existing_invitation = Mock()
        existing_invitation.invitation_id = 1
        self.db.query().filter().first.return_value = existing_invitation
        
        # Act
        result = _handle_invitation_creation_or_update(
            self.invitation_data, self.user, self.invited_user, self.db
        )
        
        # Assert
        assert result == existing_invitation
        assert existing_invitation.invitation_date == mock_now
        assert existing_invitation.suggested_role_id == self.invitation_data.suggested_role_id
        assert existing_invitation.inviter_user_id == self.user.user_id
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(existing_invitation)
        mock_delete_notifications.assert_called_once_with(existing_invitation.invitation_id)
        
    @patch('use_cases.create_invitation_use_case.datetime')
    def test_handle_invitation_create_new(self, mock_datetime):
        """Test creating new invitation"""
        # Arrange
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        self.db.query().filter().first.return_value = None
        new_invitation = Mock()
        new_invitation.invitation_id = 1
        
        # Act
        result = _handle_invitation_creation_or_update(
            self.invitation_data, self.user, self.invited_user, self.db
        )
        
        # Assert
        assert result is not None
        self.db.add.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        
    @patch('use_cases.create_invitation_use_case.delete_notifications_by_invitation_id')
    @patch('use_cases.create_invitation_use_case.datetime')
    def test_handle_invitation_update_notification_error(self, mock_datetime, mock_delete_notifications):
        """Test updating invitation when notification deletion fails"""
        # Arrange
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_delete_notifications.side_effect = Exception("Notification error")
        
        existing_invitation = Mock()
        existing_invitation.invitation_id = 1
        self.db.query().filter().first.return_value = existing_invitation
        
        # Act
        result = _handle_invitation_creation_or_update(
            self.invitation_data, self.user, self.invited_user, self.db
        )
        
        # Assert - Should still return the invitation even if notification deletion fails
        assert result == existing_invitation

    # Tests for _send_invitation_notification function
    @patch('use_cases.create_invitation_use_case.get_notification_state_by_name')
    @patch('use_cases.create_invitation_use_case.get_notification_type_by_name')
    @patch('use_cases.create_invitation_use_case.send_notification')
    def test_send_invitation_notification_success(self, mock_send, mock_get_type, mock_get_state):
        """Test successful notification sending"""
        # Arrange
        mock_get_state.return_value = {"notification_state_id": 1}
        mock_get_type.return_value = {"notification_type_id": 1}
        invitation = Mock()
        invitation.invitation_id = 1
        
        # Act
        result = _send_invitation_notification(
            invitation, self.invited_user, ROLE_ADMIN_FARM, self.farm
        )
        
        # Assert
        assert result is None
        mock_send.assert_called_once()
        
    @patch('use_cases.create_invitation_use_case.get_notification_state_by_name')
    def test_send_invitation_notification_state_not_found(self, mock_get_state):
        """Test when notification state is not found"""
        # Arrange
        mock_get_state.return_value = None
        invitation = Mock()
        invitation.invitation_id = 1
        
        # Act
        result = _send_invitation_notification(
            invitation, self.invited_user, ROLE_ADMIN_FARM, self.farm
        )
        
        # Assert
        assert result is not None
        assert result.status_code == 400
        
    @patch('use_cases.create_invitation_use_case.get_notification_state_by_name')
    @patch('use_cases.create_invitation_use_case.get_notification_type_by_name')
    def test_send_invitation_notification_type_not_found(self, mock_get_type, mock_get_state):
        """Test when notification type is not found"""
        # Arrange
        mock_get_state.return_value = {"notification_state_id": 1}
        mock_get_type.return_value = None
        invitation = Mock()
        invitation.invitation_id = 1
        
        # Act
        result = _send_invitation_notification(
            invitation, self.invited_user, ROLE_ADMIN_FARM, self.farm
        )
        
        # Assert
        assert result is not None
        assert result.status_code == 400

    # Tests for main create_invitation function
    @patch('use_cases.create_invitation_use_case._validate_farm_and_user_access')
    @patch('use_cases.create_invitation_use_case._validate_role_permissions')
    @patch('use_cases.create_invitation_use_case._validate_invited_user')
    @patch('use_cases.create_invitation_use_case._handle_invitation_creation_or_update')
    @patch('use_cases.create_invitation_use_case._send_invitation_notification')
    def test_create_invitation_success(self, mock_send_notif, mock_handle, mock_validate_user, 
                                     mock_validate_role, mock_validate_farm):
        """Test successful invitation creation"""
        # Arrange
        farm_data = {"farm": self.farm, "urf": self.urf, "urf_active_state_id": 1}
        mock_validate_farm.return_value = (farm_data, None)
        mock_validate_role.return_value = (ROLE_ADMIN_FARM, None)
        mock_validate_user.return_value = (self.invited_user, None)
        
        new_invitation = Mock()
        new_invitation.invitation_id = 1
        mock_handle.return_value = new_invitation
        mock_send_notif.return_value = None
        
        # Act
        result = create_invitation(self.invitation_data, self.user, self.db)
        
        # Assert
        assert result.status_code == 201
        mock_validate_farm.assert_called_once_with(self.invitation_data, self.user)
        mock_validate_role.assert_called_once_with(self.invitation_data, self.urf)
        mock_validate_user.assert_called_once_with(self.invitation_data, 1)
        mock_handle.assert_called_once()
        mock_send_notif.assert_called_once()
        
    @patch('use_cases.create_invitation_use_case._validate_farm_and_user_access')
    def test_create_invitation_farm_validation_error(self, mock_validate_farm):
        """Test when farm validation fails"""
        # Arrange
        error_response = Mock()
        error_response.status_code = 404
        mock_validate_farm.return_value = (None, error_response)
        
        # Act
        result = create_invitation(self.invitation_data, self.user, self.db)
        
        # Assert
        assert result == error_response
        
    @patch('use_cases.create_invitation_use_case._validate_farm_and_user_access')
    @patch('use_cases.create_invitation_use_case._validate_role_permissions')
    def test_create_invitation_role_validation_error(self, mock_validate_role, mock_validate_farm):
        """Test when role validation fails"""
        # Arrange
        farm_data = {"farm": self.farm, "urf": self.urf, "urf_active_state_id": 1}
        mock_validate_farm.return_value = (farm_data, None)
        
        error_response = Mock()
        error_response.status_code = 403
        mock_validate_role.return_value = (None, error_response)
        
        # Act
        result = create_invitation(self.invitation_data, self.user, self.db)
        
        # Assert
        assert result == error_response
        
    @patch('use_cases.create_invitation_use_case._validate_farm_and_user_access')
    @patch('use_cases.create_invitation_use_case._validate_role_permissions')
    @patch('use_cases.create_invitation_use_case._validate_invited_user')
    def test_create_invitation_user_validation_error(self, mock_validate_user, mock_validate_role, mock_validate_farm):
        """Test when invited user validation fails"""
        # Arrange
        farm_data = {"farm": self.farm, "urf": self.urf, "urf_active_state_id": 1}
        mock_validate_farm.return_value = (farm_data, None)
        mock_validate_role.return_value = (ROLE_ADMIN_FARM, None)
        
        error_response = Mock()
        error_response.status_code = 404
        mock_validate_user.return_value = (None, error_response)
        
        # Act
        result = create_invitation(self.invitation_data, self.user, self.db)
        
        # Assert
        assert result == error_response
        
    @patch('use_cases.create_invitation_use_case._validate_farm_and_user_access')
    @patch('use_cases.create_invitation_use_case._validate_role_permissions')
    @patch('use_cases.create_invitation_use_case._validate_invited_user')
    @patch('use_cases.create_invitation_use_case._handle_invitation_creation_or_update')
    def test_create_invitation_database_error(self, mock_handle, mock_validate_user, 
                                            mock_validate_role, mock_validate_farm):
        """Test when database operation fails"""
        # Arrange
        farm_data = {"farm": self.farm, "urf": self.urf, "urf_active_state_id": 1}
        mock_validate_farm.return_value = (farm_data, None)
        mock_validate_role.return_value = (ROLE_ADMIN_FARM, None)
        mock_validate_user.return_value = (self.invited_user, None)
        mock_handle.side_effect = Exception("Database error")
        
        # Act
        result = create_invitation(self.invitation_data, self.user, self.db)
        
        # Assert
        assert result.status_code == 500
        self.db.rollback.assert_called_once()
        
    @patch('use_cases.create_invitation_use_case._validate_farm_and_user_access')
    @patch('use_cases.create_invitation_use_case._validate_role_permissions')
    @patch('use_cases.create_invitation_use_case._validate_invited_user')
    @patch('use_cases.create_invitation_use_case._handle_invitation_creation_or_update')
    @patch('use_cases.create_invitation_use_case._send_invitation_notification')
    def test_create_invitation_notification_error(self, mock_send_notif, mock_handle, mock_validate_user,
                                                 mock_validate_role, mock_validate_farm):
        """Test when notification sending fails"""
        # Arrange
        farm_data = {"farm": self.farm, "urf": self.urf, "urf_active_state_id": 1}
        mock_validate_farm.return_value = (farm_data, None)
        mock_validate_role.return_value = (ROLE_ADMIN_FARM, None)
        mock_validate_user.return_value = (self.invited_user, None)
        
        new_invitation = Mock()
        new_invitation.invitation_id = 1
        mock_handle.return_value = new_invitation
        
        error_response = Mock()
        error_response.status_code = 400
        mock_send_notif.return_value = error_response
        
        # Act
        result = create_invitation(self.invitation_data, self.user, self.db)
        
        # Assert
        assert result == error_response 