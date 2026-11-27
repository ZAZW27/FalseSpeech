from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, Response
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
