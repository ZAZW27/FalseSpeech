from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
import random
import uuid
import logging
import os

from app.api.deps import get_curr_user
from app.config import jwt_expires, target_sr
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
    CreateSessionReq, UpdateSessionReq,
    DetectionSession, DetectionSegment, DetectionSessionDetail,
    OTPVerifyReq,
    ForgotPasswordReq, ResetPasswordReq,
)
from app.security.passwords import hash_pass, verify_pass
from app.service import auth, inference
from app.service.audio import preprocess_audio
from app.service.diarization import diarize_audio_tensor
from app.service.report_verify import (
    build_hr_risk_brief,
    compute_integrity_hash,
    create_batch_share_token,
    create_share_token,
    verify_share_token,
)
from app.service.conn_manager import manager
from app.service.email_service import send_otp_email, send_invoice_email
from app.service.history_export import (
    export_history_csv,
    export_history_json,
    export_history_md,
    export_history_pdf,
    export_history_txt,
)
from app.service.invoice import generate_invoice_html, generate_invoice_pdf
from app.limiter import limiter
from app.service.payment import create_payment_link, get_transaction_status

logger = logging.getLogger(__name__)
router = APIRouter()

# Urutan tier dari terendah ke tertinggi, dan kuota harian (detik) tiap tier.
# Angka kuota sama dengan yang dipakai webhook Midtrans dan /api/tiers.
TIER_ORDER = {"free": 0, "pro": 1, "pro_max": 2, "lifetime": 3}
TIER_QUOTA = {"free": 600, "pro": 18000, "pro_max": 43200, "lifetime": 9999999}
TIER_PRICE = {"free": 0, "pro": 49000, "pro_max": 99000, "lifetime": 2499000}


# Helpers -----------------------------------------------
def _user_pub(user: User) -> UserPub:
    return UserPub(
        id=str(user.id),
        name=user.name,
        email=user.email,
        phone=user.phone,
        tier=user.tier,
        balance=int(user.balance or 0),
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
    
    if _otp_expired(user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Kode OTP sudah kedaluwarsa. Silakan kirim ulang kode OTP."
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

    # Server-side platform authority check (RF-15.1):
    # Only Pro Max & Lifetime tiers may authenticate on Android.
    platform_body = (body.client_platform or "web").strip().lower()
    platform_header = request.headers.get("x-client-platform", "").strip().lower()
    if (platform_body == "android" or platform_header == "android") and user.tier not in (
        "pro_max",
        "lifetime",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your authority is not allowed for this usage",
        )

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
def get_me(user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    _sync_user_pending_transactions(db, user)
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
            price="2499000",    
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


def _effective_remaining_ratio(user: User, now_utc: datetime) -> float:
    """
    Anti-abuse proration ratio = min(time_remaining_ratio, usage_remaining_ratio).
    - Prevents near-expiry flip-flop (capped by remaining days / 30).
    - Prevents burst-usage-and-refund (capped by remaining cycle audio allowance).
    """
    tier = user.tier
    if tier == "free":
        return 0.0

    # 1. Usage remaining ratio (daily quota * 30 days; Lifetime uses 12h/day FUP * 30 baseline)
    daily_cap = 43200 if tier == "lifetime" else TIER_QUOTA.get(tier, 600)
    cycle_capacity = max(1, daily_cap * 30)
    used_in_cycle = max(0, int(getattr(user, "cycle_quota_used", 0) or 0))
    usage_ratio = max(0.0, min(1.0, 1.0 - (used_in_cycle / cycle_capacity)))

    if tier == "lifetime":
        return usage_ratio

    # 2. Time remaining ratio for monthly plans (Pro / Pro Max)
    if user.subscription_expires_at is not None:
        exp = user.subscription_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        remaining_secs = max(0.0, (exp - now_utc).total_seconds())
        time_ratio = min(1.0, remaining_secs / (30 * 86400))
    else:
        time_ratio = 1.0

    return min(time_ratio, usage_ratio)


def _current_plan_credit(user: User, now_utc: datetime) -> int:
    """Prorated IDR value of the user's currently active paid plan (time + usage adjusted)."""
    current_price = TIER_PRICE.get(user.tier, 0)
    if current_price <= 0:
        return 0
    return int(round(current_price * _effective_remaining_ratio(user, now_utc)))


@router.post("/api/subscription/upgrade", response_model=UpgradeRes, tags=["subscription"])
def upgrade(body: UpgradeReq, user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    prices = {
        "pro": 49000,
        "pro_max": 99000,
        "lifetime": 2499000
    }

    if body.target_tier not in prices:
        raise HTTPException(status_code=400, detail="Paket tidak valid")

    if user.tier == body.target_tier:
        raise HTTPException(status_code=400, detail="Anda sudah berada di paket ini")

    now_utc = datetime.now(timezone.utc)
    full_price = prices[body.target_tier]
    plan_credit = _current_plan_credit(user, now_utc)
    amount = max(0, full_price - plan_credit)
    method = (body.payment_method or "midtrans").strip().lower()
    if method not in ("midtrans", "balance", "hybrid"):
        raise HTTPException(status_code=400, detail="Metode pembayaran tidak valid")

    order_id = f"FS-{user.id}-{body.target_tier}-{uuid.uuid4().hex[:6]}"
    current_balance = int(user.balance or 0)

    # Full balance checkout (or net amount fully covered by plan credit) -> instant upgrade without Midtrans
    if amount == 0 or method == "balance" or (method == "hybrid" and current_balance >= amount):
        if current_balance < amount:
            raise HTTPException(
                status_code=400,
                detail=f"Saldo tidak mencukupi (dibutuhkan Rp {amount:,} setelah kredit paket Rp {plan_credit:,}, saldo Anda Rp {current_balance:,})",
            )

        user.balance = current_balance - amount
        user.tier = body.target_tier
        user.quota_limit = TIER_QUOTA[body.target_tier]
        user.cycle_quota_used = 0  # Fresh billing cycle on upgrade
        if body.target_tier in ("pro", "pro_max"):
            # Upgraders get a fresh 30-day cycle starting today (old remaining days were already credited!)
            user.subscription_expires_at = now_utc + timedelta(days=30)
        elif body.target_tier == "lifetime":
            user.subscription_expires_at = None

        invoice_html = generate_invoice_html(
            user_name=user.name,
            order_id=order_id,
            amount=amount,
            tier=body.target_tier,
            user_email=user.email,
            is_downgrade=False,
            issued_at=now_utc,
        )
        db.add(
            TransactionRow(
                user_id=user.id,
                order_id=order_id,
                amount=amount,
                status="success",
                invoice_html=invoice_html,
            )
        )
        db.commit()
        db.refresh(user)

        try:
            import threading, asyncio
            threading.Thread(
                target=lambda: asyncio.run(send_invoice_email(user.email, invoice_html)),
                daemon=True,
            ).start()
        except Exception as e:
            logger.warning(f"Invoice email background dispatch skipped: {e}")

        logger.info(
            f"Balance Upgrade: user {user.id} -> {body.target_tier} "
            f"(plan_credit={plan_credit}, spent={amount}, new_balance={user.balance})"
        )
        return UpgradeRes(
            payment_url=None,
            paid_with_balance=True,
            plan_credit_idr=plan_credit,
            balance_used_idr=amount,
            remaining_midtrans_idr=0,
            new_balance=user.balance,
            order_id=order_id,
        )

    # Hybrid (current plan credit + available balance + Midtrans for remaining) or Midtrans (after plan credit)
    # IMPORTANT: Do NOT deduct user.balance yet! Only deduct inside _apply_paid_transaction() once Midtrans settles.
    balance_used = min(current_balance, amount) if method == "hybrid" else 0
    midtrans_amount = amount - balance_used

    try:
        payment_data = create_payment_link(
            order_id=order_id,
            amount=midtrans_amount,
            tier_name=body.target_tier,
            user_email=user.email
        )

        new_transaction = TransactionRow(
            user_id=user.id,
            order_id=order_id,
            amount=amount,
            balance_applied=balance_used,
            status="pending",
            payment_url=payment_data["redirect_url"],
        )
        db.add(new_transaction)
        db.commit()

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return UpgradeRes(
        payment_url=payment_data["redirect_url"],
        paid_with_balance=False,
        plan_credit_idr=plan_credit,
        balance_used_idr=balance_used,
        remaining_midtrans_idr=midtrans_amount,
        new_balance=current_balance,
        order_id=order_id,
    )


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

    now_utc = datetime.now(timezone.utc)
    previous_tier = user.tier
    adjustment_cost_idr = 0  # SC-07: no prorated fee charged on downgrade

    # Prorated downgrade compensation = (current_price - target_price) * min(time_ratio, usage_ratio)
    price_diff = max(0, TIER_PRICE.get(previous_tier, 0) - TIER_PRICE.get(body.target_tier, 0))
    remaining_ratio = _effective_remaining_ratio(user, now_utc)

    compensation_idr = int(round(price_diff * remaining_ratio))
    user.balance = int(user.balance or 0) + compensation_idr

    user.tier = body.target_tier
    user.quota_limit = TIER_QUOTA[body.target_tier]
    if body.target_tier == "free":
        user.subscription_expires_at = None
        user.cycle_quota_used = 0
    elif previous_tier == "lifetime":
        # Leaving Lifetime for a monthly plan starts a real 30-day clock (no eternal null expiry)
        user.subscription_expires_at = now_utc + timedelta(days=30)
        user.cycle_quota_used = 0
    # Monthly -> Monthly downgrade (e.g. Pro Max -> Pro): intentionally SHARES the same subscription_expires_at date pool!

    # Record downgrade & official credit note in transactions history
    dg_order_id = f"FS-{user.id}-{body.target_tier}-DG-{uuid.uuid4().hex[:6]}"
    dg_invoice_html = generate_invoice_html(
        user_name=user.name,
        order_id=dg_order_id,
        amount=compensation_idr,
        tier=body.target_tier,
        user_email=user.email,
        is_downgrade=True,
        previous_tier=previous_tier,
        issued_at=now_utc,
    )
    db.add(
        TransactionRow(
            user_id=user.id,
            order_id=dg_order_id,
            amount=compensation_idr,
            status="downgrade",
            invoice_html=dg_invoice_html,
        )
    )
    db.commit()

    logger.info(
        f"Downgrade: user {user.id} {previous_tier} -> {body.target_tier} "
        f"(quota={user.quota_limit}, compensation={compensation_idr}, balance={user.balance})"
    )
    return DowngradeRes(
        success=True,
        effective_at=now_utc,
        previous_tier=previous_tier,
        new_tier=user.tier,
        new_quota_limit=user.quota_limit,
        adjustment_cost_idr=adjustment_cost_idr,
        compensation_idr=compensation_idr,
        new_balance=user.balance,
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
    _sync_user_pending_transactions(db, user)
    trxs = db.query(TransactionRow).filter(
        TransactionRow.user_id == user.id,
        TransactionRow.status.in_(["success", "downgrade", "pending"]),
    ).order_by(TransactionRow.created_at.desc()).all()
    
    return [
        Invoice(
            invoice_id=str(t.id),
            order_id=t.order_id,
            amount_idr=t.amount,
            status=t.status,
            issued_at=t.created_at,
            paid_at=t.created_at if t.status != "pending" else None,
            tier=t.order_id.split("-")[2],
            payment_url=t.payment_url if t.status == "pending" else None,
        ) for t in trxs
    ]


@router.post("/api/billing/cancel/{order_id}", tags=["subscription"])
def cancel_pending_transaction(order_id: str, user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    trx = (
        db.query(TransactionRow)
        .filter(TransactionRow.order_id == order_id)
        .filter(TransactionRow.user_id == user.id)
        .filter(TransactionRow.status == "pending")
        .first()
    )
    if trx is None:
        raise HTTPException(status_code=404, detail="Transaksi pending tidak ditemukan")
    trx.status = "cancelled"
    db.commit()
    return {"cancelled": True, "order_id": order_id}


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


@router.get("/api/billing/invoice/{order_id}/pdf", tags=["subscription"])
def get_invoice_pdf(order_id: str, user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    trx = (
        db.query(TransactionRow)
        .filter(TransactionRow.order_id == order_id)
        .filter(TransactionRow.user_id == user.id)
        .first()
    )
    if trx is None:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")

    parts = trx.order_id.split("-")
    tier = parts[2] if len(parts) >= 3 else user.tier
    is_downgrade = trx.status == "downgrade"
    pdf_bytes = generate_invoice_pdf(
        user_name=user.name,
        order_id=trx.order_id,
        amount=trx.amount,
        tier=tier,
        user_email=user.email,
        is_downgrade=is_downgrade,
        issued_at=trx.created_at,
    )
    filename = f"FalseSpeech-{'CreditNote' if is_downgrade else 'Invoice'}-{trx.order_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


# Pre-Recorded Audio Upload, Auto Speaker Diarization & Client-Chunked Detection -----------------------------------------------
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB for single-shot legacy upload; chunked mode handles 1GB+ client-side!


@router.post("/api/detect/diarize", tags=["detection"])
async def diarize_uploaded_audio(
    file: UploadFile = File(...),
    max_speakers: int = Form(4),
    user: User = Depends(get_curr_user),
):
    """
    Runs lightweight Silero VAD + MFCC speaker clustering sequentially BEFORE spoofing detection.
    Client sends compressed 8kHz/16kHz mono audio so even long Zoom/Meet recordings stay tiny.
    """
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Audio payload is empty.")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Diarization payload exceeds 50 MB.")

    wav_tensor = preprocess_audio(raw_bytes, target_sr=target_sr, device=None)
    if wav_tensor is None or wav_tensor.shape[1] < int(target_sr * 0.5):
        raise HTTPException(status_code=400, detail="Could not decode audio for speaker detection.")

    import asyncio

    segments = await asyncio.to_thread(
        diarize_audio_tensor,
        wav_tensor,
        target_sr,
        max(1, min(6, int(max_speakers or 4))),
    )
    unique_speakers = len({s["label"] for s in segments})
    return {
        "duration_s": round(wav_tensor.shape[1] / float(target_sr), 2),
        "speakers_detected": unique_speakers,
        "segments": segments,
    }


@router.post("/api/detect/chunk", tags=["detection"])
async def detect_single_chunk(
    file: UploadFile = File(...),
    session_id: int = Form(...),
    chunk_index: int = Form(1),
    start_s: float = Form(0.0),
    end_s: float = Form(0.0),
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    """
    Client-chunked detection endpoint for large (1GB+) recordings:
    Browser keeps the full file in client RAM, downsamples to lossless 16kHz mono WAV chunks,
    and streams small chunks here one-by-one into an existing DetectionSessionRow.
    """
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="AI model is still loading. Please try again shortly.")

    sess = (
        db.query(DetectionSessionRow)
        .filter(DetectionSessionRow.id == session_id, DetectionSessionRow.user_id == user.id)
        .first()
    )
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Empty audio chunk.")

    _, device_used = inference.get_model()
    wav_tensor = preprocess_audio(raw_bytes, target_sr=target_sr, device=device_used)
    if wav_tensor is None or wav_tensor.shape[1] < int(target_sr * 0.3):
        raise HTTPException(status_code=400, detail="Could not decode audio chunk.")

    chunk_seconds = wav_tensor.shape[1] / float(target_sr)
    now_utc = datetime.now(timezone.utc)
    if user.quota_reset_at is None or user.quota_reset_at.replace(tzinfo=timezone.utc) < now_utc:
        user.quota_used = 0
        user.quota_reset_at = now_utc.replace(hour=23, minute=59, second=59, microsecond=0)
        db.commit()

    would_be_used = int(user.quota_used or 0) + max(1, int(round(chunk_seconds)))
    if user.tier == "lifetime" and would_be_used > 43200:
        raise HTTPException(
            status_code=403,
            detail="Fair Usage Policy exceeded. Lifetime users are limited to 12 hours of audio analysis per day.",
        )
    if would_be_used > user.quota_limit:
        raise HTTPException(status_code=403, detail="Daily quota exceeded.")

    ril_prob, fek_prob = await inference.enqueue_inference(wav_tensor, user.tier)
    is_fake = fek_prob > 0.5

    seg = DetectionSegmentRow(
        session_id=sess.id,
        offset_s=int(chunk_index),
        duration_s=round(chunk_seconds, 2),
        is_fake=is_fake,
        fake_prob=float(fek_prob),
        real_prob=float(ril_prob),
        recorded_at=now_utc,
    )
    db.add(seg)
    db.flush()

    all_segs = (
        db.query(DetectionSegmentRow)
        .filter(DetectionSegmentRow.session_id == sess.id)
        .all()
    )
    total_c = len(all_segs)
    fake_count = sum(1 for s in all_segs if s.is_fake)
    real_count = total_c - fake_count
    avg_fake = sum(float(s.fake_prob or 0.0) for s in all_segs) / total_c if total_c else 0.0
    if total_c == 0:
        verdict = "real"
    elif fake_count / total_c >= 0.5:
        verdict = "fake"
    elif fake_count / total_c <= 0.1:
        verdict = "real"
    else:
        verdict = "mixed"

    sess.fake_count = fake_count
    sess.real_count = real_count
    sess.avg_fake_prob = avg_fake
    sess.verdict = verdict
    sess.ended_at = now_utc
    sess.duration_s = max(1, int(round(sum(float(s.duration_s or 0.0) for s in all_segs))))

    add_sec = max(1, int(round(chunk_seconds)))
    user.quota_used = int(user.quota_used or 0) + add_sec
    user.cycle_quota_used = int(user.cycle_quota_used or 0) + add_sec
    db.commit()

    return {
        "session_id": str(sess.id),
        "chunk_index": int(chunk_index),
        "start_s": round(float(start_s), 2),
        "end_s": round(float(end_s), 2),
        "duration_s": round(chunk_seconds, 2),
        "fake_prob": float(fek_prob),
        "real_prob": float(ril_prob),
        "is_fake": is_fake,
        "session_verdict": verdict,
        "session_fake_ratio": avg_fake,
        "quota_used": user.quota_used,
        "quota_limit": user.quota_limit,
    }


@router.post("/api/detect/upload", tags=["detection"])
async def detect_uploaded_audio(
    file: UploadFile = File(...),
    chunk_size: int = Form(5),
    title: str | None = Form(None),
    segments_json: str | None = Form(None),
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    if not inference.is_loaded():
        raise HTTPException(status_code=503, detail="AI model is still loading. Please try again shortly.")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds the 50 MB upload limit.")

    _, device_used = inference.get_model()
    wav_tensor = preprocess_audio(raw_bytes, target_sr=target_sr, device=device_used)
    if wav_tensor is None or wav_tensor.shape[1] < int(target_sr * 0.5):
        raise HTTPException(
            status_code=400,
            detail="Could not decode audio file or audio is shorter than 0.5 seconds.",
        )

    total_samples = int(wav_tensor.shape[1])
    total_duration_s = total_samples / float(target_sr)
    safe_chunk_s = max(1, min(15, int(chunk_size or 5)))

    # Reset daily quota if past quota_reset_at
    now_utc = datetime.now(timezone.utc)
    if user.quota_reset_at is None or user.quota_reset_at.replace(tzinfo=timezone.utc) < now_utc:
        user.quota_used = 0
        user.quota_reset_at = now_utc.replace(hour=23, minute=59, second=59, microsecond=0)
        db.commit()

    # Determine clips: either user-defined manual speaker sections OR whole recording
    base_name = (title or "").strip()
    if not base_name:
        fname = os.path.basename(file.filename or "Recorded Audio")
        base_name = os.path.splitext(fname)[0].strip() or "Recorded Audio"

    clips: list[dict] = []
    if segments_json and segments_json.strip():
        try:
            parsed = json.loads(segments_json)
            if not isinstance(parsed, list):
                raise ValueError("segments_json must be a list")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid segments_json payload.")

        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                continue
            start_s = max(0.0, min(total_duration_s, float(item.get("start_s", 0.0))))
            end_s = max(0.0, min(total_duration_s, float(item.get("end_s", total_duration_s))))
            if end_s - start_s < 0.5:
                continue
            label = str(item.get("label") or f"Speaker {idx + 1}").strip()[:80]
            clips.append(
                {
                    "title": f"{base_name} - {label}"[:160],
                    "label": label,
                    "start_s": start_s,
                    "end_s": end_s,
                }
            )

    if not clips:
        clips = [
            {
                "title": base_name[:160],
                "label": "Full Recording",
                "start_s": 0.0,
                "end_s": total_duration_s,
            }
        ]

    # Quota & Fair Usage Policy check across total selected audio seconds
    requested_seconds = int(round(sum(c["end_s"] - c["start_s"] for c in clips)))
    if user.tier == "lifetime" and (user.quota_used + requested_seconds) > 43200:
        raise HTTPException(
            status_code=403,
            detail="Fair Usage Policy exceeded. Lifetime users are limited to 12 hours of audio analysis per day.",
        )
    if (user.quota_used + requested_seconds) > user.quota_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Daily quota exceeded ({user.quota_used}/{user.quota_limit}s used).",
        )

    sessions_out = []
    chunk_samples = safe_chunk_s * target_sr
    min_tail_samples = int(0.6 * target_sr)

    for clip in clips:
        s_idx = int(round(clip["start_s"] * target_sr))
        e_idx = min(total_samples, int(round(clip["end_s"] * target_sr)))
        clip_tensor = wav_tensor[:, s_idx:e_idx]
        clip_len = int(clip_tensor.shape[1])
        if clip_len < int(0.5 * target_sr):
            continue

        # Slice into chunk_size-second tensors (merge tiny trailing sliver into previous chunk)
        ranges: list[tuple[int, int]] = []
        pos = 0
        while pos < clip_len:
            nxt = min(clip_len, pos + chunk_samples)
            if ranges and (nxt - pos) < min_tail_samples:
                prev_s, _ = ranges[-1]
                ranges[-1] = (prev_s, nxt)
            else:
                ranges.append((pos, nxt))
            pos = nxt

        sess = DetectionSessionRow(
            user_id=user.id,
            title=clip["title"],
            notes=f"Uploaded file ({clip['label']}: {clip['start_s']:.1f}s - {clip['end_s']:.1f}s)",
            source="upload",
            started_at=now_utc,
            ended_at=now_utc,
            duration_s=max(1, int(round(clip["end_s"] - clip["start_s"]))),
            fake_count=0,
            real_count=0,
            avg_fake_prob=0.0,
            verdict="real",
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)

        chunk_results = []
        fake_count = 0
        real_count = 0
        total_fake_prob = 0.0

        for idx, (c_start, c_end) in enumerate(ranges, start=1):
            sub_tensor = clip_tensor[:, c_start:c_end]
            dur_s = round((c_end - c_start) / float(target_sr), 2)
            ril_prob, fek_prob = await inference.enqueue_inference(sub_tensor, user.tier)
            is_fake = fek_prob > 0.5
            total_fake_prob += float(fek_prob)
            if is_fake:
                fake_count += 1
            else:
                real_count += 1

            seg = DetectionSegmentRow(
                session_id=sess.id,
                offset_s=idx,
                duration_s=dur_s,
                is_fake=is_fake,
                fake_prob=float(fek_prob),
                real_prob=float(ril_prob),
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(seg)
            chunk_results.append(
                {
                    "chunk_index": idx,
                    "start_s": round(clip["start_s"] + c_start / float(target_sr), 2),
                    "end_s": round(clip["start_s"] + c_end / float(target_sr), 2),
                    "duration_s": dur_s,
                    "fake_prob": float(fek_prob),
                    "real_prob": float(ril_prob),
                    "is_fake": is_fake,
                }
            )

        total_c = fake_count + real_count
        avg_fake = (total_fake_prob / total_c) if total_c > 0 else 0.0
        if total_c == 0:
            verdict = "real"
        elif fake_count / total_c >= 0.5:
            verdict = "fake"
        elif fake_count / total_c <= 0.1:
            verdict = "real"
        else:
            verdict = "mixed"

        sess.fake_count = fake_count
        sess.real_count = real_count
        sess.avg_fake_prob = avg_fake
        sess.verdict = verdict
        sess.ended_at = datetime.now(timezone.utc)
        db.commit()

        sessions_out.append(
            {
                "session_id": str(sess.id),
                "title": sess.title,
                "label": clip["label"],
                "start_s": round(clip["start_s"], 2),
                "end_s": round(clip["end_s"], 2),
                "duration": sess.duration_s,
                "fake_ratio": avg_fake,
                "verdict": verdict,
                "fake_count": fake_count,
                "real_count": real_count,
                "chunks": chunk_results,
            }
        )

    user.quota_used = int(user.quota_used or 0) + requested_seconds
    user.cycle_quota_used = int(user.cycle_quota_used or 0) + requested_seconds
    db.commit()

    return {
        "total_duration_s": round(total_duration_s, 2),
        "quota_used": user.quota_used,
        "quota_limit": user.quota_limit,
        "sessions": sessions_out,
    }


# Detection History -----------------------------------------------
def _parse_iso_dt(value: str | None, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        # Handle YYYY-MM-DD date-only strings cleanly
        if len(raw) == 10:
            dt = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
            if end_of_day:
                dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _query_filtered_sessions(
    db: Session,
    user_id: int,
    verdict: str | None = None,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    source: str | None = None,
    limit: int = 200,
) -> list[DetectionSessionRow]:
    q = db.query(DetectionSessionRow).filter(DetectionSessionRow.user_id == user_id)

    if verdict and verdict.lower() != "all":
        v = verdict.lower()
        if v == "has_fake":
            q = q.filter(DetectionSessionRow.fake_count > 0)
        elif v in ("real", "fake", "mixed"):
            q = q.filter(DetectionSessionRow.verdict == v)

    if source and source.lower() != "all":
        q = q.filter(DetectionSessionRow.source == source.lower())

    dt_start = _parse_iso_dt(start_date, end_of_day=False)
    if dt_start is not None:
        q = q.filter(DetectionSessionRow.started_at >= dt_start)

    dt_end = _parse_iso_dt(end_date, end_of_day=True)
    if dt_end is not None:
        q = q.filter(DetectionSessionRow.started_at <= dt_end)

    rows = q.order_by(DetectionSessionRow.id.desc()).limit(min(max(limit, 1), 500)).all()

    if search and search.strip():
        needle = search.strip().lower().lstrip("#")
        filtered = []
        for r in rows:
            haystack = " ".join(
                [
                    str(r.id),
                    r.title or "",
                    r.notes or "",
                    r.source or "",
                    r.verdict or "",
                    r.started_at.isoformat() if r.started_at else "",
                ]
            ).lower()
            if needle in haystack:
                filtered.append(r)
        return filtered

    return rows


def _serialize_session(db: Session, r: DetectionSessionRow) -> DetectionSession:
    segs = (
        db.query(DetectionSegmentRow)
        .filter(DetectionSegmentRow.session_id == r.id)
        .all()
    )
    total_chunks = len(segs) or int(r.fake_count or 0) + int(r.real_count or 0)
    max_fake = max((float(s.fake_prob or 0.0) for s in segs), default=float(r.avg_fake_prob or 0.0))
    return DetectionSession(
        session_id=str(r.id),
        started_at=r.started_at,
        ended_at=r.ended_at,
        duration=r.duration_s,
        fake_ratio=float(r.avg_fake_prob or 0.0),
        verdict=r.verdict,
        title=r.title,
        notes=r.notes,
        source=r.source or "web",
        fake_count=int(r.fake_count or 0),
        real_count=int(r.real_count or 0),
        total_chunks=total_chunks,
        max_fake_prob=max_fake,
    )


@router.post("/api/history/sessions", response_model=DetectionSession, status_code=status.HTTP_201_CREATED, tags=["history"])
def create_detection_session(
    body: CreateSessionReq | None = None,
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    payload = body or CreateSessionReq()
    row = DetectionSessionRow(
        user_id=user.id,
        title=(payload.title or "").strip() or None,
        source=(payload.source or "web").strip().lower()[:32] or "web",
        fake_count=0,
        real_count=0,
        avg_fake_prob=0.0,
        verdict="real",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_session(db, row)


@router.get("/api/history", response_model=list[DetectionSession], tags=["history"])
def detection_history(
    verdict: str | None = None,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    source: str | None = None,
    limit: int = 200,
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    rows = _query_filtered_sessions(
        db=db,
        user_id=user.id,
        verdict=verdict,
        search=search,
        start_date=start_date,
        end_date=end_date,
        source=source,
        limit=limit,
    )
    return [_serialize_session(db, r) for r in rows]


@router.get("/api/history/export", tags=["history"])
def export_detection_history(
    format: str = "csv",
    session_id: str | None = None,
    session_ids: str | None = None,
    verdict: str | None = None,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    source: str | None = None,
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    fmt = (format or "csv").strip().lower()
    if fmt not in ("csv", "pdf", "txt", "json", "md"):
        raise HTTPException(status_code=400, detail="Unsupported export format. Use csv, pdf, txt, md, or json.")

    if session_ids and session_ids.strip():
        parsed_ids = []
        for tok in session_ids.split(","):
            tok = tok.strip()
            if tok.isdigit():
                parsed_ids.append(int(tok))
        if not parsed_ids:
            raise HTTPException(status_code=400, detail="No valid session_ids provided.")
        rows = (
            db.query(DetectionSessionRow)
            .filter(DetectionSessionRow.user_id == user.id, DetectionSessionRow.id.in_(parsed_ids))
            .order_by(DetectionSessionRow.id.desc())
            .all()
        )
    elif session_id:
        try:
            sid = int(session_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Session tidak ditemukan")
        row = (
            db.query(DetectionSessionRow)
            .filter(DetectionSessionRow.id == sid, DetectionSessionRow.user_id == user.id)
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Session tidak ditemukan")
        rows = [row]
    else:
        rows = _query_filtered_sessions(
            db=db,
            user_id=user.id,
            verdict=verdict,
            search=search,
            start_date=start_date,
            end_date=end_date,
            source=source,
            limit=500,
        )

    items = []
    for r in rows:
        segs = (
            db.query(DetectionSegmentRow)
            .filter(DetectionSegmentRow.session_id == r.id)
            .order_by(DetectionSegmentRow.offset_s.asc(), DetectionSegmentRow.id.asc())
            .all()
        )
        items.append((r, segs))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    suffix = (
        f"selected-{len(rows)}"
        if session_ids
        else f"session-{session_id}"
        if session_id
        else f"report-{stamp}"
    )

    if fmt == "csv":
        content = export_history_csv(items, user.name, user.email)
        media_type = "text/csv; charset=utf-8"
        ext = "csv"
    elif fmt == "pdf":
        content = export_history_pdf(items, user.name, user.email)
        media_type = "application/pdf"
        ext = "pdf"
    elif fmt == "txt":
        content = export_history_txt(items, user.name, user.email)
        media_type = "text/plain; charset=utf-8"
        ext = "txt"
    elif fmt == "md":
        content = export_history_md(items, user.name, user.email)
        media_type = "text/markdown; charset=utf-8"
        ext = "md"
    else:
        content = export_history_json(items, user.name, user.email)
        media_type = "application/json; charset=utf-8"
        ext = "json"

    filename = f"FalseSpeech-HR-{suffix}.{ext}"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


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
        .order_by(DetectionSegmentRow.offset_s.asc(), DetectionSegmentRow.id.asc())
        .all()
    )
    return DetectionSessionDetail(
        session_id=str(row.id),
        title=row.title,
        notes=row.notes,
        source=row.source or "web",
        started_at=row.started_at,
        ended_at=row.ended_at,
        duration=row.duration_s,
        fake_ratio=float(row.avg_fake_prob or 0.0),
        verdict=row.verdict,
        fake_count=int(row.fake_count or 0),
        real_count=int(row.real_count or 0),
        segments=[
            DetectionSegment(
                id=s.id,
                offset=s.offset_s,
                duration_s=float(getattr(s, "duration_s", 0.0) or 0.0),
                is_fake=s.is_fake,
                fake_prob=s.fake_prob,
                real_prob=float(s.real_prob or 0.0),
                recorded_at=getattr(s, "recorded_at", None) or row.started_at,
            )
            for s in segs
        ],
    )


@router.patch("/api/history/{session_id}", response_model=DetectionSession, tags=["history"])
def update_detection_session(
    session_id: str,
    body: UpdateSessionReq,
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    try:
        sid = int(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    row = (
        db.query(DetectionSessionRow)
        .filter(DetectionSessionRow.id == sid, DetectionSessionRow.user_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    if body.title is not None:
        row.title = body.title.strip() or None
    if body.notes is not None:
        row.notes = body.notes.strip() or None

    db.commit()
    db.refresh(row)
    return _serialize_session(db, row)


@router.delete("/api/history/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["history"])
def delete_detection_session(
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
        .filter(DetectionSessionRow.id == sid, DetectionSessionRow.user_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    db.delete(row)
    db.commit()
    return None


@router.post("/api/history/{session_id}/share", tags=["history"])
def create_session_share_link(
    session_id: str,
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    """Generates a 30-day HMAC-SHA256 signed read-only share link and SHA-256 integrity digest."""
    try:
        sid = int(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    row = (
        db.query(DetectionSessionRow)
        .filter(DetectionSessionRow.id == sid, DetectionSessionRow.user_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    segs = (
        db.query(DetectionSegmentRow)
        .filter(DetectionSegmentRow.session_id == row.id)
        .order_by(DetectionSegmentRow.offset_s.asc(), DetectionSegmentRow.id.asc())
        .all()
    )
    token = create_share_token(row.id, user.id, expires_days=30)
    digest = compute_integrity_hash(row, segs)
    return {
        "session_id": str(row.id),
        "share_token": token,
        "share_path": f"/verify/{token}",
        "integrity_hash": digest,
        "expires_in_days": 30,
    }


@router.post("/api/history/share-batch", tags=["history"])
async def create_batch_session_share_link(
    request: Request,
    user: User = Depends(get_curr_user),
    db: Session = Depends(get_db),
):
    """Generates a single 30-day HMAC-SHA256 signed share link covering multiple selected sessions."""
    body = await request.json()
    raw_ids = body.get("session_ids") if isinstance(body, dict) else None
    if not isinstance(raw_ids, list) or not raw_ids:
        raise HTTPException(status_code=400, detail="Select at least one session to share.")

    parsed_ids = []
    for x in raw_ids:
        try:
            parsed_ids.append(int(x))
        except (ValueError, TypeError):
            continue

    rows = (
        db.query(DetectionSessionRow)
        .filter(DetectionSessionRow.user_id == user.id, DetectionSessionRow.id.in_(parsed_ids))
        .order_by(DetectionSessionRow.id.desc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No matching sessions found.")

    valid_ids = [r.id for r in rows]
    token = create_batch_share_token(valid_ids, user.id, expires_days=30)
    return {
        "session_ids": [str(i) for i in valid_ids],
        "count": len(valid_ids),
        "share_token": token,
        "share_path": f"/verify/{token}",
        "expires_in_days": 30,
    }


@router.get("/api/verify/{share_token}", tags=["history"])
def verify_shared_report(
    share_token: str,
    db: Session = Depends(get_db),
):
    """Public read-only verification endpoint for single or multi-session bundles (no login required)."""
    verified = verify_share_token(share_token)
    if verified is None:
        raise HTTPException(status_code=404, detail="Verification link is invalid or has expired.")

    sids, uid = verified
    rows = (
        db.query(DetectionSessionRow)
        .filter(DetectionSessionRow.id.in_(sids), DetectionSessionRow.user_id == uid)
        .order_by(DetectionSessionRow.id.desc())
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="The shared detection session(s) no longer exist.")

    owner = db.query(User).filter(User.id == uid).first()
    reviewed_by = owner.name if owner else "False Speech User"

    def _build_entry(row):
        segs = (
            db.query(DetectionSegmentRow)
            .filter(DetectionSegmentRow.session_id == row.id)
            .order_by(DetectionSegmentRow.offset_s.asc(), DetectionSegmentRow.id.asc())
            .all()
        )
        return {
            "verified": True,
            "integrity_hash": compute_integrity_hash(row, segs),
            "reviewed_by": reviewed_by,
            "session_id": str(row.id),
            "title": (row.title or "").strip() or f"Session #{row.id}",
            "notes": row.notes or "",
            "source": row.source or "web",
            "started_at": row.started_at,
            "ended_at": row.ended_at,
            "duration": row.duration_s,
            "fake_ratio": float(row.avg_fake_prob or 0.0),
            "verdict": row.verdict,
            "fake_count": int(row.fake_count or 0),
            "real_count": int(row.real_count or 0),
            "total_chunks": len(segs),
            "hr_brief": build_hr_risk_brief(row, segs),
            "segments": [
                {
                    "id": s.id,
                    "offset": s.offset_s,
                    "duration_s": float(getattr(s, "duration_s", 0.0) or 0.0),
                    "is_fake": bool(s.is_fake),
                    "fake_prob": float(s.fake_prob or 0.0),
                    "real_prob": float(s.real_prob or 0.0),
                    "recorded_at": getattr(s, "recorded_at", None) or row.started_at,
                }
                for s in segs
            ],
        }

    entries = [_build_entry(r) for r in rows]
    if len(entries) == 1:
        return {**entries[0], "is_batch": False, "sessions": entries}

    import hashlib
    bundle_digest = hashlib.sha256(":".join(e["integrity_hash"] for e in entries).encode("ascii")).hexdigest()
    return {
        "verified": True,
        "is_batch": True,
        "reviewed_by": reviewed_by,
        "total_sessions": len(entries),
        "integrity_hash": bundle_digest,
        "sessions": entries,
    }


# Payment Finalization & Webhook -----------------------------------------------
def _is_midtrans_paid(transaction_status: str | None, fraud_status: str | None) -> bool:
    return transaction_status == "settlement" or (
        transaction_status == "capture" and fraud_status == "accept"
    )


def _apply_paid_transaction(db: Session, trx: TransactionRow, user: User | None = None) -> bool:
    """Idempotently upgrades the user's tier, quota, expiry, and generates invoice HTML."""
    if not trx or trx.status == "success":
        return False

    parts = trx.order_id.split("-")
    if len(parts) < 3:
        return False
    user_id = int(parts[1])
    target_tier = parts[2]

    if user is None:
        user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    now_utc = datetime.now(timezone.utc)
    # Deduct reserved hybrid balance ONLY now that Midtrans confirmed settlement/capture
    applied = int(getattr(trx, "balance_applied", 0) or 0)
    if applied > 0:
        user.balance = max(0, int(user.balance or 0) - applied)

    previous_tier = user.tier
    user.tier = target_tier
    user.cycle_quota_used = 0

    if target_tier in ("pro", "pro_max"):
        user.quota_limit = TIER_QUOTA[target_tier]
        if previous_tier == target_tier:
            # Same-tier renewal (Extend): stack +30 days onto existing expiry
            exp = user.subscription_expires_at
            if exp and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            base_dt = exp if (exp and exp > now_utc) else now_utc
            user.subscription_expires_at = base_dt + timedelta(days=30)
        else:
            # Tier upgrade: fresh 30-day cycle starting today (old plan's remaining value was already credited!)
            user.subscription_expires_at = now_utc + timedelta(days=30)
    elif target_tier == "lifetime":
        user.quota_limit = 9999999
        user.subscription_expires_at = None

    trx.status = "success"
    invoice_html = generate_invoice_html(
        user_name=user.name,
        order_id=trx.order_id,
        amount=trx.amount,
        tier=target_tier,
        user_email=user.email,
        is_downgrade=False,
        issued_at=trx.created_at,
    )
    trx.invoice_html = invoice_html
    db.commit()
    db.refresh(user)

    try:
        import asyncio
        loop = asyncio.get_running_loop()
        loop.create_task(send_invoice_email(user.email, invoice_html))
    except RuntimeError:
        # Called from a sync route threadpool; send invoice email in a background thread.
        import threading, asyncio
        threading.Thread(
            target=lambda: asyncio.run(send_invoice_email(user.email, invoice_html)),
            daemon=True,
        ).start()

    logger.info(f"Payment Finalized: User {user_id} upgraded to {target_tier} (order={trx.order_id})")
    return True


def _sync_user_pending_transactions(db: Session, user: User) -> int:
    """Checks Midtrans Status API for any pending transactions belonging to this user."""
    pending_trxs = (
        db.query(TransactionRow)
        .filter(TransactionRow.user_id == user.id, TransactionRow.status == "pending")
        .order_by(TransactionRow.created_at.asc())
        .all()
    )
    if not pending_trxs:
        return 0

    finalized = 0
    for trx in pending_trxs:
        status_res = get_transaction_status(trx.order_id)
        if not status_res:
            continue
        tx_status = status_res.get("transaction_status")
        fraud_status = status_res.get("fraud_status")
        if _is_midtrans_paid(tx_status, fraud_status):
            if _apply_paid_transaction(db, trx, user=user):
                finalized += 1
        elif tx_status in ("deny", "cancel", "expire", "failure"):
            trx.status = "failed"
            db.commit()
    return finalized


@router.post("/api/payment/sync", tags=["subscription"])
def sync_my_payments(user: User = Depends(get_curr_user), db: Session = Depends(get_db)):
    synced = _sync_user_pending_transactions(db, user)
    return {"synced": synced, "user": _user_pub(user)}


@router.post("/api/payment/webhook", tags=["subscription"])
async def midtrans_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()

    transaction_status = payload.get("transaction_status")
    order_id = payload.get("order_id")
    fraud_status = payload.get("fraud_status")

    if _is_midtrans_paid(transaction_status, fraud_status):
        try:
            trx = db.query(TransactionRow).filter(TransactionRow.order_id == order_id).first()
            _apply_paid_transaction(db, trx)
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")

    return {"status": "ok"}
