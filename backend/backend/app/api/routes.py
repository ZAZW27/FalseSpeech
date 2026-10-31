from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_curr_user
from app.config import jwt_expires
from app.db.models import (
    User,
    DetectionSessionRow,
    DetectionSegmentRow,
)
from app.db.session import get_db
from app.schemas import (
    HealthCheck,
    RegisterReq, RegisterRes,
    LoginReq, LoginRes,
    UserPub, UpdateProfileRequest,
    Tier, UpgradeReq, UpgradeRes,
    DowngradeReq, DowngradeRes,
    Invoice,
    DetectionSession, DetectionSegment, DetectionSessionDetail,
)
from app.service import auth, inference

router = APIRouter()


# Helpers -----------------------------------------------
def _user_pub(user: User) -> UserPub:
    return UserPub(
        id=str(user.id),
        name=user.name,
        email=user.email,
        phone=user.phone,
        tier=user.tier,
        quota_used=user.quota_used,
        quota_limit=user.quota_limit,
        quota_reset_at=user.quota_reset_at,
    )


# Health -----------------------------------------------
@router.get("/", response_model=HealthCheck, tags=["health"])
def health():
    _, device_used = inference.get_model()
    return HealthCheck(
        status="ok",
        model_loaded=inference.is_loaded(),
        device=str(device_used) if device_used else None,
    )


# Auth -----------------------------------------------
@router.post("/api/auth/register", response_model=RegisterRes, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(body: RegisterReq, db: Session = Depends(get_db)):
    try:
        user = auth.daftar_user(
            db,
            name=body.name,
            email=body.email,
            phone=body.phone,
            password=body.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return RegisterRes(user_id=str(user.id), email=user.email)


@router.post("/api/auth/login", response_model=LoginRes, tags=["auth"])
def login(body: LoginReq, db: Session = Depends(get_db)):
    token = auth.login_user(db, body.email_or_phone, body.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email/nomor telepon atau password salah",
        )

    user = auth.cari_user_by_email_or_phone(db, body.email_or_phone)
    return LoginRes(
        access_token=token,
        token_type="bearer",
        expires_in=jwt_expires * 60,
        user=_user_pub(user),
    )


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def logout(user: User = Depends(get_curr_user)):
    return None


# User -----------------------------------------------
@router.get("/api/users/me", response_model=UserPub, tags=["user"])
def get_me(user: User = Depends(get_curr_user)):
    return _user_pub(user)


@router.patch("/api/users/me", response_model=UserPub, tags=["user"])
def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        user.name = body.name
    if body.phone is not None:
        user.phone = body.phone
    db.commit()
    db.refresh(user)
    return _user_pub(user)


# Tiers and Subscription -----------------------------------------------
@router.get("/api/tiers", response_model=list[Tier], tags=["subscription"])
def list_tiers():
    return [
        Tier(
            id="free",
            name="Free",
            price="0",
            quota_seconds_daily=600,
            features=["live_detection_basic", "history_7d"],
        ),
        Tier(
            id="pro",
            name="Pro",
            price="49000",
            quota_seconds_daily=18000,
            features=[
                "live_detection_basic",
                "confidence_score",
                "history_30d",
            ],
        ),
        Tier(
            id="pro_max",
            name="Pro Max",
            price="99000",
            quota_seconds_daily=43200,
            features=[
                "live_detection_basic",
                "confidence_score",
                "history_90d",
                "android_widget",
            ],
        ),
        Tier(
            id="lifetime",
            name="Lifetime",
            price="2500000",    
            quota_seconds_daily=0,
            features=[
                "live_detection_basic",
                "confidence_score",
                "history_unlimited",
                "android_widget",
                "fair_use_policy",
            ],
        ),
    ]

@router.post("/api/subscription/upgrade", response_model=UpgradeRes, tags=["subscription"])
def upgrade(body: UpgradeReq, user: User = Depends(get_curr_user)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.post("/api/subscription/downgrade", response_model=DowngradeRes, tags=["subscription"])
def downgrade(body: DowngradeReq, user: User = Depends(get_curr_user)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.get("/api/billing/history", response_model=list[Invoice],
            tags=["subscription"])
def billing_history(user: User = Depends(get_curr_user)):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


# Detection History -----------------------------------------------
@router.get("/api/history", response_model=list[DetectionSession], tags=["history"])
def detection_history(
        user: User = Depends(get_curr_user),
        db: Session = Depends(get_db),
    ):
    rows = (
        db.query(DetectionSessionRow)
        .filter(DetectionSessionRow.user_id == user.id)
        .order_by(DetectionSessionRow.id.desc())
        .limit(100)
        .all()
    )
    result = []
    for r in rows:
        total = (r.fake_count or 0) + (r.real_count or 0)
        ratio = (r.fake_count / total) if total > 0 else 0.0
        result.append(
            DetectionSession(
                session_id=str(r.id),
                started_at=r.started_at,
                duration=r.duration_s,
                fake_ratio=ratio,
                verdict=r.verdict,
            )
        )
    return result


@router.get("/api/history/{session_id}", response_model=DetectionSessionDetail,tags=["history"])
def detection_history_detail(
        session_id: str,
        user: User = Depends(get_curr_user),
        db: Session = Depends(get_db),
    ):
    try:
        sid = int(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    row = (
        db.query(DetectionSessionRow)
        .filter(DetectionSessionRow.id == sid)
        .filter(DetectionSessionRow.user_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    segs = (
        db.query(DetectionSegmentRow)
        .filter(DetectionSegmentRow.session_id == row.id)
        .order_by(DetectionSegmentRow.offset_s.asc())
        .all()
    )
    return DetectionSessionDetail(
        session_id=str(row.id),
        segments=[
            DetectionSegment(
                offset=s.offset_s,
                is_fake=s.is_fake,
                fake_prob=s.fake_prob,
            )
            for s in segs
        ],
    )