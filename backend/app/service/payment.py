import logging
from midtransclient import Snap
from app.config import midtrans_server_key, midtrans_is_production

logger = logging.getLogger(__name__)

# Inisialisasi Snap Midtrans
snap = Snap(
    is_production=midtrans_is_production,
    server_key=midtrans_server_key,
)

def create_payment_link(order_id: str, amount: int, tier_name: str, user_email: str) -> dict:
    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": amount
        },
        "item_details": [{
            "id": tier_name.lower(),
            "price": amount,
            "quantity": 1,
            "name": f"False Speech - {tier_name.upper()}"
        }],
        "customer_details": {
            "email": user_email
        }
    }
    
    try:
        transaction = snap.create_transaction(param)
        return {"redirect_url": transaction['redirect_url'], "token": transaction['token']}
    except Exception as e:
        logger.error(f"Midtrans error: {e}")
        raise ValueError("Gagal membuat link pembayaran")