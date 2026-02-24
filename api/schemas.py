from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

# User Profile Schemas
class UserProfileBase(BaseModel):
    upi_id: Optional[str] = None
    mobile_number: Optional[str] = None
    is_staff: bool = False

class UserProfileResponse(UserProfileBase):
    wallet_balance: Decimal
    class Config:
        from_attributes = True

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(UserBase):
    password: str = Field(..., max_length=72)
    upi_id: Optional[str] = None
    mobile_number: Optional[str] = None
    vehicle_number: Optional[str] = None

class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    upi_id: Optional[str] = None
    mobile_number: Optional[str] = None
    wallet_balance: Optional[Decimal] = None
    is_staff: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    profile: Optional[UserProfileResponse] = None
    vehicles: List[VehicleResponse] = []
    class Config:
        from_attributes = True

# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Vehicle Schemas
class VehicleBase(BaseModel):
    plate_number: str

class VehicleCreate(VehicleBase):
    pass

class VehicleResponse(VehicleBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True

# Violation Schemas
class ViolationResponse(BaseModel):
    id: int
    vehicle_id: int
    image: str
    amount: Decimal
    status: str
    created: datetime
    class Config:
        from_attributes = True

class AdminViolationUpdate(BaseModel):
    amount: Optional[Decimal] = None
    status: Optional[str] = None

# Wallet Schemas
class WalletDeposit(BaseModel):
    amount: Decimal

# Admin Vehicle Schemas
class AdminVehicleCreate(VehicleBase):
    owner_id: Optional[int] = None

class AdminVehicleUpdate(VehicleBase):
    owner_id: Optional[int] = None
