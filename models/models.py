from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class InvitationStates(Base):
    __tablename__ = 'invitation_states'
    invitation_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    invitations = relationship("Invitations", back_populates="state")

class Invitations(Base):
    __tablename__ = 'invitations'
    __table_args__ = (UniqueConstraint('email', 'farm_id'),)

    invitation_id = Column(Integer, primary_key=True)
    email = Column(String(150), nullable=False)
    suggested_role_id = Column(Integer, ForeignKey('roles.role_id'), nullable=False)
    invitation_state_id = Column(Integer, ForeignKey('invitation_states.invitation_state_id'), nullable=False)
    farm_id = Column(Integer, ForeignKey('farms.farm_id'), nullable=False)
    inviter_user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    invitation_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relaciones
    farm = relationship("Farms", back_populates="invitations")
    state = relationship('InvitationStates', back_populates="invitations")
    inviter = relationship("Users", foreign_keys=[inviter_user_id], back_populates="created_invitations")
    notifications = relationship("Notifications", back_populates="invitation")
    suggested_role = relationship('Roles', back_populates="invitations")
