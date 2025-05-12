from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Date, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Invitations(Base):
    __tablename__ = 'invitations'
    __table_args__ = (UniqueConstraint('invited_user_id', 'farm_id'),)

    invitation_id = Column(Integer, primary_key=True)
    invited_user_id = Column(Integer, nullable=False)
    suggested_role_id = Column(Integer, nullable=False)
    farm_id = Column(Integer, nullable=False)
    inviter_user_id = Column(Integer, nullable=False)
    invitation_date = Column(DateTime(timezone=True), nullable=False)