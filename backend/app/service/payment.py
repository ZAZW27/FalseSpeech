import logging
import os
from midtransclient import Snap
from app.config import midtrans_server_key, midtrans_is_production

logger = logging.getLogger(__name__)

# Inisialisasi Snap Midtrans
snap = Snap(
    is_production=midtrans_is_production,
    server_key=midtrans_server_key,
)


def create_payment_link(order_id: str, amount: int, tier_name: str, user_email: str) -> dict:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": amount,
        },
        "item_details": [{
            "id": tier_name.lower(),
            "price": amount,
            "quantity": 1,
            "name": f"False Speech - {tier_name.upper()}",
        }],
        "customer_details": {
            "email": user_email,
        },
        "callbacks": {
            "finish": f"{frontend_url}/payment/finish",
        },
    }

    try:
        transaction = snap.create_transaction(param)
        return {"redirect_url": transaction["redirect_url"], "token": transaction["token"]}
    except Exception as e:
        logger.error(f"Midtrans error: {e}")
        raise ValueError("Gagal membuat link pembayaran")


def get_transaction_status(order_id: str) -> dict | None:
    """Query Midtrans Status API directly so paid orders finalize even if webhook cannot reach localhost."""
    try:
        return snap.transactions.status(order_id)
    except Exception as e:
        logger.warning(f"Midtrans status check skipped for {order_id}: {e}")
        return None
