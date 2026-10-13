from fastapi import APIRouter, HTTPException

from app.service import inference
from app.schemas import (
    HealthCheck,
    RegisterReq, RegisterRes,
    LoginReq, LoginRes,
    UserPub, UpdateProfileRequest,
    Tier, UpgradeReq, UpgradeRes,
    DowngradeReq, DowngradeRes,
    Invoice,
    DetectionSession, DetectionSessionDetail,
)

router = APIRouter()

# Health --------------------------------------------------------
@router.get("/", response_model=HealthCheck, tags=["health"])
def health():
    _, device = inference.get_model()
    return HealthCheck(
        status="ok",
        model_loaded=inference.is_loaded(),
        device=str(device) if device else None,
    )

# Auth -----------------------------------------------------------
@router.post("/api/auth/register", response_model=RegisterRes,status_code=201, tags=["auth"])
def register(body: RegisterReq):
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/api/auth/login", response_model=LoginRes, tags=["auth"])
def login(body: LoginReq):
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/api/auth/logout", status_code=204, tags=["auth"])
def logout():
    raise HTTPException(status_code=501, detail="Not implemented yet")

# User -----------------------------------------------------------
@router.get("/api/users/me", response_model=UserPub, tags=["user"])
def get_me():
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.patch("/api/users/me", response_model=UserPub, tags=["user"])
def update_me(body: UpdateProfileRequest):
    raise HTTPException(status_code=501, detail="Not implemented yet")

# Tiers and Subscription ------------------------------------------
@router.get("/api/tiers", response_model=list[Tier], tags=["subscription"])
def list_tiers():
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/api/subscription/upgrade", response_model=UpgradeRes,
             tags=["subscription"])
def upgrade(body: UpgradeReq):
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/api/subscription/downgrade", response_model=DowngradeRes,
             tags=["subscription"])
def downgrade(body: DowngradeReq):
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/api/billing/history", response_model=list[Invoice],
            tags=["subscription"])
def billing_history():
    raise HTTPException(status_code=501, detail="Not implemented yet")

# Detection History -----------------------------------------------
@router.get("/api/history", response_model=list[DetectionSession],
            tags=["history"])
def detection_history():
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/api/history/{session_id}", response_model=DetectionSessionDetail,
            tags=["history"])
def detection_history_detail(session_id: str):
    raise HTTPException(status_code=501, detail="Not implemented yet")