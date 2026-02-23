from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, DateTime, func
from sqlalchemy.orm import relationship
from database import Base
from decimal import Decimal

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    vehicles = relationship("Vehicle", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    upi_id = Column(String, nullable=True)
    wallet_balance = Column(Numeric(precision=12, scale=2), default=Decimal('0.00'))
    is_staff = Column(Boolean, default=False)
    mobile_number = Column(String, nullable=True)

    user = relationship("User", back_populates="profile")

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plate_number = Column(String, unique=True, index=True)

    user = relationship("User", back_populates="vehicles")
    violations = relationship("Violation", back_populates="vehicle")

class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    image = Column(String)
    amount = Column(Numeric(precision=10, scale=2))
    status = Column(String, default="pending")
    created = Column(DateTime(timezone=True), server_default=func.now())

    vehicle = relationship("Vehicle", back_populates="violations")
