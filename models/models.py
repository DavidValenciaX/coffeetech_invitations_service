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
    __table_args__ = (UniqueConstraint('invited_user_id', 'entity_type', 'entity_id'),)

    invitation_id = Column(Integer, primary_key=True)
    invited_user_id = Column(Integer, nullable=False)
    suggested_role_id = Column(Integer, nullable=False)
    invitation_state_id = Column(Integer, ForeignKey('invitation_states.invitation_state_id'), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    inviter_user_id = Column(Integer, nullable=False)
    invitation_date = Column(DateTime(timezone=True), nullable=False)
    
    # Relationship
    state = relationship('InvitationStates', back_populates="invitations")