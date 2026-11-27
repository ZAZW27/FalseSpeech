from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

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
    client_platform: str = "web"

    @field_validator('email_or_phone')
    @classmethod
    def validate_email_or_phone(cls, v):
        # Cek apakah formatnya email
        if '@' in v:
            # Validasi email secara manual
            email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
            if not re.match(email_regex, v):
                raise ValueError('Format email tidak valid')
        else:
            # Cek apakah formatnya nomor telepon (hanya angka, minimal 8 digit)
            if not re.match(r'^\d{8,15}$', v):
                raise ValueError('Format email atau nomor telepon tidak valid')
        return v

class UserPub(BaseModel): 
    id: str
    name: str
    email: str
    phone: str
    tier: str
    balance: int = 0
    quota_used: int
    quota_limit: int
    quota_reset_at: Optional[datetime] = None
    subscription_expires_at: Optional[datetime] = None

class LoginRes(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPub
    
class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

class ChangePasswordReq(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

class ChangePasswordRes(BaseModel):
    success: bool
    message: str

# Subscribes
class Tier(BaseModel): 
    id: str
    name: str
    price: str
    quota_seconds_daily: int
    features: List[str]

class UpgradeReq(BaseModel):  # upgrade
    target_tier: str
    payment_method: str = "midtrans"  # "midtrans" | "balance" | "hybrid"

class UpgradeRes(BaseModel):
    payment_url: Optional[str] = None
    paid_with_balance: bool = False
    plan_credit_idr: int = 0
    balance_used_idr: int = 0
    remaining_midtrans_idr: int = 0
    new_balance: Optional[int] = None
    order_id: Optional[str] = None
    
class DowngradeReq(BaseModel): # Downgrade 
    target_tier: str
    
class DowngradeRes(BaseModel):
    success: bool
    effective_at: datetime
    previous_tier: str
    new_tier: str
    new_quota_limit: int
    adjustment_cost_idr: int = 0
    compensation_idr: int = 0
    new_balance: int = 0

# Billings
class Invoice(BaseModel): 
    invoice_id: str
    order_id: str  # dipakai frontend untuk GET /api/billing/invoice/{order_id}
    amount_idr: int
    status: str
    issued_at: datetime
    paid_at: Optional[datetime] = None
    tier: str
    payment_url: Optional[str] = None

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

class OTPVerifyReq(BaseModel):
    email: EmailStr
    otp_code: str

# Forgot & reset password
class ForgotPasswordReq(BaseModel):
    email: EmailStr

class ResetPasswordReq(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)
