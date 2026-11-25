from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import hmac
import secrets
from datetime import datetime, timedelta, timezone
import random
import uuid
import logging

from app.api.deps import get_curr_user
from app.config import jwt_expires
from app.db.models import (
    User,
    DetectionSessionRow,
    DetectionSegmentRow,
    TransactionRow, 
)
from app.db.session import get_db
from app.schemas import (
    HealthCheck,
    RegisterReq, RegisterRes,
    LoginReq, LoginRes,
    UserPub, UpdateProfileRequest,
    ChangePasswordReq, ChangePasswordRes,
    Tier, UpgradeReq, UpgradeRes,
    DowngradeReq, DowngradeRes,
    Invoice,
    DetectionSession, DetectionSegment, DetectionSessionDetail,
    OTPVerifyReq,
    ForgotPasswordReq, ResetPasswordReq,
)
from app.security.passwords import hash_pass, verify_pass
from app.service import auth, inference
from app.service.conn_manager import manager
from app.service.email_service import send_otp_email, send_invoice_email
from app.service.invoice import generate_invoice_html
from app.limiter import limiter
from app.service.payment import create_payment_link

logger = logging.getLogger(__name__)
router = APIRouter()

# Urutan tier dari terendah ke tertinggi, dan kuota harian (detik) tiap tier.
# Angka kuota sama dengan yang dipakai webhook Midtrans dan /api/tiers.
TIER_ORDER = {"free": 0, "pro": 1, "pro_max": 2, "lifetime": 3}
TIER_QUOTA = {"free": 600, "pro": 18000, "pro_max": 43200, "lifetime": 9999999}


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
        subscription_expires_at=user.subscription_expires_at,
    )


def _otp_expired(user: User) -> bool:
    # Kolom DateTime kadang kembali tanpa tzinfo, anggap UTC.
    if user.otp_expires_at is None:
        return True
    expires_at = user.otp_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > expires_at


# Health -----------------------------------------------
@router.get("/", response_model=HealthCheck, tags=["health"])
def health():
    _, device_used = inference.get_model()
    return HealthCheck(
        status="ok",
        model_loaded=inference.is_loaded(),
        device=str(device_used) if device_used else None,
    )


# Auth & OTP -----------------------------------------------
@router.post("/api/auth/register/send-otp", tags=["auth"])
async def register_send_otp(body: RegisterReq, db: Session = Depends(get_db)):
    otp = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    existing_user = auth.cari_user_by_email(db, body.email)
    
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Email sudah terdaftar dan terverifikasi. Silakan login."
            )

        phone_owner = auth.cari_user_by_phone(db, body.phone)
        if phone_owner and phone_owner.id != existing_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Nomor HP sudah terdaftar di akun lain."
            )

        existing_user.name = body.name
        existing_user.phone = body.phone
        existing_user.hashed_password = auth.hash_pass(body.password)
        existing_user.otp_code = otp
        existing_user.otp_expires_at = expires_at
        db.commit()
        
        await send_otp_email(existing_user.email, otp)
        return {"message": "Kode OTP baru telah dikirim ulang ke email Anda."}

    if auth.cari_user_by_phone(db, body.phone):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Nomor HP sudah terdaftar."
        )
    
    user = User(
        name=body.name, 
        email=body.email, 
        phone=body.phone,
        hashed_password=auth.hash_pass(body.password),
        otp_code=otp,
        otp_expires_at=expires_at,
        is_verified=False
    )
    db.add(user)
    db.commit()
    
    await send_otp_email(user.email, otp)
    return {"message": "OTP berhasil dikirim ke email"}


@router.post("/api/auth/register/verify-otp", response_model=RegisterRes, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register_verify_otp(body: OTPVerifyReq, db: Session = Depends(get_db)):
    user = auth.cari_user_by_email(db, body.email)
    
    if not user or user.otp_code != body.otp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Kode OTP salah"
        )
    
    if user.otp_expires_at and datetime.now(timezone.utc) > user.otp_expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Kode OTP sudah kedaluwarsa"
        )
        
    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()
    
    return RegisterRes(user_id=str(user.id), email=user.email)


@router.post("/api/auth/forgot-password", tags=["auth"])
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ForgotPasswordReq, db: Session = Depends(get_db)):
    user = auth.cari_user_by_email(db, body.email)

    # Hanya akun terverifikasi yang boleh reset password.
    if user and user.is_verified:
        otp = str(secrets.randbelow(900000) + 100000)
        user.otp_code = otp
        user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.commit()

        try:
            await send_otp_email(user.email, otp)
        except Exception as e:
            logger.error(f"Gagal mengirim OTP reset password: {e}")

    # Respons selalu sama, supaya orang lain tidak bisa mengecek email mana yang terdaftar.
    return {"message": "Jika email terdaftar, kode OTP telah dikirim."}


@router.post("/api/auth/reset-password", tags=["auth"])
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordReq, db: Session = Depends(get_db)):
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Kode OTP salah atau sudah kedaluwarsa",
    )

    user = auth.cari_user_by_email(db, body.email)
    if not user or not user.is_verified or not user.otp_code:
        raise invalid

    if not hmac.compare_digest(user.otp_code, body.otp_code):
        raise invalid

    if _otp_expired(user):
        raise invalid

    user.hashed_password = auth.hash_pass(body.new_password)
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()

    return {"message": "Password berhasil diubah. Silakan login."}


@router.post("/api/auth/login", response_model=LoginRes, tags=["auth"])
@limiter.limit("5/minute")
def login(request: Request, body: LoginReq, db: Session = Depends(get_db)):
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


@router.patch("/api/users/change-password", response_model=ChangePasswordRes, tags=["user"])
def change_password(
    body: ChangePasswordReq,
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    if not verify_pass(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi saat ini salah",
        )
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kata sandi baru harus berbeda dari kata sandi saat ini",
        )

    user.hashed_password = hash_pass(body.new_password)
    db.commit()
    logger.info(f"Password changed for user {user.id}")
    return ChangePasswordRes(success=True, message="Kata sandi berhasil diperbarui")


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
def upgrade(body: UpgradeReq, user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    prices = {
        "pro": 49000,
        "pro_max": 99000,
        "lifetime": 2500000
    }
    
    if body.target_tier not in prices:
        raise HTTPException(status_code=400, detail="Paket tidak valid")
        
    if user.tier == body.target_tier:
        raise HTTPException(status_code=400, detail="Anda sudah berada di paket ini")

    amount = prices[body.target_tier]
    
    order_id = f"FS-{user.id}-{body.target_tier}-{uuid.uuid4().hex[:6]}"
    
    try:
        payment_data = create_payment_link(
            order_id=order_id,
            amount=amount,
            tier_name=body.target_tier,
            user_email=user.email
        )
        
        new_transaction = TransactionRow(
            user_id=user.id,
            order_id=order_id,
            amount=amount,
            status="pending"
        )
        db.add(new_transaction)
        db.commit()
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return UpgradeRes(payment_url=payment_data['redirect_url'])


@router.post("/api/subscription/downgrade", response_model=DowngradeRes, tags=["subscription"])
def downgrade(body: DowngradeReq, user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    if body.target_tier not in TIER_ORDER:
        raise HTTPException(status_code=400, detail="Paket tidak valid")

    current_rank = TIER_ORDER.get(user.tier, 0)
    target_rank = TIER_ORDER[body.target_tier]

    if target_rank >= current_rank:
        raise HTTPException(
            status_code=400,
            detail="Paket tujuan harus lebih rendah dari paket Anda saat ini",
        )

    # Countermeasure: prevent tier/quota downgrade while an active WebSocket stream is open
    if user.id in manager.active_connections:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hentikan sesi pemantauan aktif sebelum menurunkan paket",
        )

    previous_tier = user.tier
    adjustment_cost_idr = 0  # SC-07: no prorated fee on downgrade
    user.tier = body.target_tier
    user.quota_limit = TIER_QUOTA[body.target_tier]
    if body.target_tier == "free":
        user.subscription_expires_at = None
    db.commit()

    logger.info(
        f"Downgrade: user {user.id} {previous_tier} -> {body.target_tier} "
        f"(quota={user.quota_limit}, adjustment_cost={adjustment_cost_idr})"
    )
    return DowngradeRes(
        success=True,
        effective_at=datetime.now(timezone.utc),
        previous_tier=previous_tier,
        new_tier=user.tier,
        new_quota_limit=user.quota_limit,
        adjustment_cost_idr=adjustment_cost_idr,
    )


@router.post("/api/subscription/extend", response_model=UpgradeRes, tags=["subscription"])
def extend_subscription(user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    """UC-05 / RF-04: Generates a Midtrans payment link to extend an active Pro / Pro Max plan by 30 days."""
    monthly_prices = {
        "pro": 49000,
        "pro_max": 99000,
    }
    if user.tier not in monthly_prices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perpanjangan bulanan hanya tersedia untuk paket Pro atau Pro Max",
        )

    amount = monthly_prices[user.tier]
    order_id = f"FS-{user.id}-{user.tier}-{uuid.uuid4().hex[:6]}"

    try:
        payment_data = create_payment_link(
            order_id=order_id,
            amount=amount,
            tier_name=user.tier,
            user_email=user.email,
        )
        new_transaction = TransactionRow(
            user_id=user.id,
            order_id=order_id,
            amount=amount,
            status="pending",
        )
        db.add(new_transaction)
        db.commit()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return UpgradeRes(payment_url=payment_data["redirect_url"])


@router.get("/api/billing/history", response_model=list[Invoice], tags=["subscription"])
def billing_history(user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    trxs = db.query(TransactionRow).filter(
        TransactionRow.user_id == user.id, 
        TransactionRow.status == "success"
    ).order_by(TransactionRow.created_at.desc()).all()
    
    return [
        Invoice(
            invoice_id=str(t.id),
            order_id=t.order_id,
            amount_idr=t.amount,
            status=t.status,
            issued_at=t.created_at,
            paid_at=t.created_at,
            tier=t.order_id.split("-")[2]
        ) for t in trxs
    ]


@router.get("/api/billing/invoice/{order_id}", response_class=HTMLResponse, tags=["subscription"])
def get_invoice(order_id: str, user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    # Filter user_id di query: transaksi milik user lain sama saja dengan tidak ada (404).
    trx = (
        db.query(TransactionRow)
        .filter(TransactionRow.order_id == order_id)
        .filter(TransactionRow.user_id == user.id)
        .first()
    )
    if trx is None or not trx.invoice_html:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")

    return HTMLResponse(content=trx.invoice_html, headers={"Cache-Control": "private, no-store"})


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
        result.append(
            DetectionSession(
                session_id=str(r.id),
                started_at=r.started_at,
                duration=r.duration_s,
                fake_ratio=float(r.avg_fake_prob or 0.0),
                verdict=r.verdict,
            )
        )
    return result


@router.get("/api/history/{session_id}", response_model=DetectionSessionDetail, tags=["history"])
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


# Webhook -----------------------------------------------
@router.post("/api/payment/webhook", tags=["subscription"])
async def midtrans_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    
    transaction_status = payload.get("transaction_status")
    order_id = payload.get("order_id")
    fraud_status = payload.get("fraud_status")
    
    if transaction_status == "settlement" or (transaction_status == "capture" and fraud_status == "accept"):
        try:
            trx = db.query(TransactionRow).filter(TransactionRow.order_id == order_id).first()
            if not trx or trx.status == "success":
                return {"status": "ok"} 
                
            parts = order_id.split("-")
            user_id = int(parts[1])
            target_tier = parts[2]
            
            user = db.query(User).filter(User.id == user_id).first()
            
            if user:
                user.tier = target_tier
                
                if target_tier == "pro":
                    user.quota_limit = 18000
                    base_dt = (
                        user.subscription_expires_at
                        if user.subscription_expires_at and user.subscription_expires_at > datetime.now(timezone.utc)
                        else datetime.now(timezone.utc)
                    )
                    user.subscription_expires_at = base_dt + timedelta(days=30)
                elif target_tier == "pro_max":
                    user.quota_limit = 43200
                    base_dt = (
                        user.subscription_expires_at
                        if user.subscription_expires_at and user.subscription_expires_at > datetime.now(timezone.utc)
                        else datetime.now(timezone.utc)
                    )
                    user.subscription_expires_at = base_dt + timedelta(days=30)
                elif target_tier == "lifetime":
                    user.quota_limit = 9999999
                    user.subscription_expires_at = None
                    
                trx.status = "success"
                
                invoice_html = generate_invoice_html(user.name, order_id, trx.amount, target_tier)
                trx.invoice_html = invoice_html
                
                db.commit()
                
                import asyncio
                asyncio.create_task(send_invoice_email(user.email, invoice_html))
                
                logger.info(f"Webhook Success: User {user_id} upgraded to {target_tier}!")
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            
    return {"status": "ok"}
