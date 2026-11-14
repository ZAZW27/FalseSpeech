def generate_invoice_html(user_name: str, order_id: str, amount: int, tier: str) -> str:
    # HTML ini akan disimpen di DB dan dikirim ke Email
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
        <h2 style="color: #202734; text-align: center;">FALSE SPEECH</h2>
        <h3 style="color: #10b981; text-align: center;">INVOICE PEMBAYARAN</h3>
        <hr style="border: 1px solid #eee;" />
        
        <table style="width: 100%; font-size: 14px; margin-bottom: 20px;">
            <tr>
                <td><strong>Nama Pelanggan:</strong></td>
                <td style="text-align: right;">{user_name}</td>
            </tr>
            <tr>
                <td><strong>Order ID:</strong></td>
                <td style="text-align: right;">{order_id}</td>
            </tr>
            <tr>
                <td><strong>Paket Langganan:</strong></td>
                <td style="text-align: right;">{tier.upper()}</td>
            </tr>
            <tr>
                <td><strong>Total Pembayaran:</strong></td>
                <td style="text-align: right; font-weight: bold; color: #10b981;">Rp {amount:,.0f}</td>
            </tr>
            <tr>
                <td><strong>Status:</strong></td>
                <td style="text-align: right; color: green;">LUNAS</td>
            </tr>
        </table>
        
        <p style="font-size: 12px; color: #888; text-align: center;">
            Terima kasih telah berlangganan False Speech. Invoice ini sah dan dibuat secara otomatis oleh sistem.
        </p>
    </div>
    """
    return html