from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# Cek kondisi model
class HealthCheck(BaseModel):
    status: str
    model_loaded: bool
    device: Optional[str] = None

# Auth
class RegisterReq(BaseModel): 
    name: str = Field(..., min_length = 1, max_length = 100)
    email: EmailStr
    phone: str = Field(..., min_length=8, max_length = 20)
    password: str = Field(..., min_length=8)
    
class RegisterRes(BaseModel): 
    user_id: str
    email: str

class LoginReq(BaseModel):
    email_or_phone: str
    password: str

class UserPub(BaseModel): 
    id: str
    name: str
    email: str
    phone: str
    tier: str
    quota_used: int
    quota_limit: int
    quota_reset_at: datetime

class LoginRes(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPub
    
class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

# Subscribes
class Tier(BaseModel): 
    id: str
    name: str
    price: str
    quota_seconds_daily: int
    features: List[str]

class UpgradeReq(BaseModel):  # upgrade
    target_tier: str

class UpgradeRes(BaseModel):
    payment_url: str
    
class DowngradeReq(BaseModel): # Downgrade 
    target_tier: str
    
class DowngradeRes(BaseModel): 
    success: bool
    effective_at: datetime

# Billings
class Invoice(BaseModel): 
    invoice_id: str
    amount_idr: int
    status: str
    issued_at: datetime
    paid_at: Optional[datetime] = None
    tier: str

# Loggings
class DetectionSession(BaseModel): 
    session_id: str
    started_at: datetime
    duration: float
    fake_ratio: float
    verdict: str
    
class DetectionSegment(BaseModel): 
    offset: float # seconds
    is_fake: bool
    fake_prob: float

class DetectionSessionDetail(BaseModel): 
    session_id: str
    segments: List[DetectionSegment]

# Websockets
class WSDetectionResult(BaseModel): 
    real_prob: float
    fake_prob: float
    is_fake: bool
    
class WSError(BaseModel): 
    error: str





