from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import os
from pydantic import EmailStr

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("SMTP_EMAIL"),
    MAIL_PASSWORD=os.getenv("SMTP_PASSWORD"),
    MAIL_FROM=os.getenv("SMTP_EMAIL"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

async def send_otp_email(email: str, otp: str):
    html = f"""
    <div style="font-family: sans-serif; padding: 20px;">
        <h2>Verifikasi Akun False Speech</h2>
        <p>Kode OTP kamu adalah: <b style="font-size: 24px; color: #10b981;">{otp}</b></p>
        <p>Kode ini berlaku selama 5 menit.</p>
    </div>
    """
    message = MessageSchema(
        subject="Kode OTP Registrasi",
        recipients=[email],
        body=html,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)