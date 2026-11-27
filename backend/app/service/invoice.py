from datetime import datetime, timezone
from html import escape
from typing import Optional

from fpdf import FPDF

TIER_NAMES = {
    "free": "Free Plan",
    "pro": "Pro Plan (Monthly)",
    "pro_max": "Pro Max Plan (Monthly)",
    "lifetime": "Lifetime Plan (One-Time License)",
}


def _fmt_idr(amount: int) -> str:
    return f"Rp {int(amount or 0):,}".replace(",", ".")


def generate_invoice_html(
    user_name: str,
    order_id: str,
    amount: int,
    tier: str,
    user_email: str = "",
    is_downgrade: bool = False,
    previous_tier: Optional[str] = None,
    issued_at: Optional[datetime] = None,
) -> str:
    """Generates a formal, print/PDF-ready official HTML invoice or downgrade credit note."""
    dt = issued_at or datetime.now(timezone.utc)
    date_str = dt.strftime("%d %B %Y, %H:%M UTC")
    safe_name = escape(user_name or "Valued Customer")
    safe_email = escape(user_email or "-")
    safe_order = escape(order_id)
    tier_display = TIER_NAMES.get(tier, tier.replace("_", " ").title())
    prev_display = TIER_NAMES.get(previous_tier or "", (previous_tier or "").replace("_", " ").title())

    doc_title = "OFFICIAL CREDIT NOTE" if is_downgrade else "OFFICIAL PAYMENT INVOICE"
    doc_subtitle = (
        "NOTA PENYESUAIAN & KOMPENSASI PAKET LANGGANAN"
        if is_downgrade
        else "FAKTUR RESMI PEMBAYARAN LANGGANAN"
    )
    status_label = "CREDITED / PENYESUAIAN" if is_downgrade else "PAID / LUNAS"
    status_color = "#2563eb" if is_downgrade else "#15803d"
    status_bg = "#eff6ff" if is_downgrade else "#f0fdf4"
    item_desc = (
        f"Plan Downgrade ({prev_display} &rarr; {tier_display}) — Prorated Balance Credit"
        if is_downgrade
        else f"False Speech Subscription — {tier_display}"
    )
    amount_prefix = "+" if is_downgrade else ""
    total_label = "Total Credited to Balance" if is_downgrade else "Total Amount Paid"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{doc_title} - {safe_order}</title>
  <style>
    @page {{ size: A4; margin: 18mm; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px 16px;
      background: #f1f5f9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      color: #0f172a;
    }}
    .toolbar {{
      max-width: 760px;
      margin: 0 auto 16px;
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }}
    .btn {{
      background: #202734;
      color: #b7d894;
      border: 1px solid #36415a;
      border-radius: 8px;
      padding: 10px 18px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }}
    .sheet {{
      max-width: 760px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }}
    .header {{
      background: #202734;
      color: #ffffff;
      padding: 28px 32px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
    }}
    .brand {{ font-size: 22px; font-weight: 800; letter-spacing: 0.04em; color: #b7d894; }}
    .company {{ font-size: 12px; color: #cbd5e1; margin-top: 6px; line-height: 1.5; }}
    .doc-meta {{ text-align: right; }}
    .doc-title {{ font-size: 16px; font-weight: 800; letter-spacing: 0.06em; }}
    .doc-sub {{ font-size: 11px; color: #94a3b8; margin-top: 4px; }}
    .body {{ padding: 28px 32px; }}
    .meta-grid {{
      display: flex;
      justify-content: space-between;
      gap: 20px;
      padding-bottom: 20px;
      border-bottom: 1px solid #e2e8f0;
      font-size: 13px;
    }}
    .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; font-weight: 700; }}
    .val {{ margin-top: 4px; font-weight: 600; color: #0f172a; }}
    .stamp {{
      display: inline-block;
      margin-top: 8px;
      padding: 4px 12px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.06em;
      color: {status_color};
      background: {status_bg};
      border: 1px solid {status_color};
    }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 24px; font-size: 13.5px; }}
    th {{
      text-align: left;
      padding: 11px 12px;
      background: #f8fafc;
      border-top: 1px solid #cbd5e1;
      border-bottom: 1px solid #cbd5e1;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #475569;
    }}
    td {{ padding: 14px 12px; border-bottom: 1px solid #e2e8f0; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .totals {{
      margin-top: 18px;
      margin-left: auto;
      width: 300px;
      font-size: 13.5px;
    }}
    .totals-row {{ display: flex; justify-content: space-between; padding: 6px 0; }}
    .totals-final {{
      border-top: 2px solid #202734;
      margin-top: 6px;
      padding-top: 10px;
      font-size: 15px;
      font-weight: 800;
      color: #202734;
    }}
    .footer {{
      margin-top: 32px;
      padding-top: 18px;
      border-top: 1px solid #e2e8f0;
      font-size: 11.5px;
      color: #64748b;
      line-height: 1.6;
    }}
    .sig-box {{
      margin-top: 26px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      font-size: 12px;
    }}
    .sig-line {{ border-top: 1px solid #94a3b8; padding-top: 6px; width: 220px; text-align: center; }}
    @media print {{
      body {{ background: #ffffff; padding: 0; }}
      .toolbar {{ display: none !important; }}
      .sheet {{ box-shadow: none; border: none; }}
    }}
  </style>
</head>
<body>
  <div class="toolbar">
    <button class="btn" onclick="window.print()">Print / Save as PDF</button>
  </div>
  <div class="sheet">
    <div class="header">
      <div>
        <div class="brand">FALSE SPEECH</div>
        <div class="company">
          PT False Speech Teknologi Indonesia<br />
          Real-Time AI Deepfake Voice Verification Platform<br />
          billing@falsespeech.app &bull; Official Electronic Billing System
        </div>
      </div>
      <div class="doc-meta">
        <div class="doc-title">{doc_title}</div>
        <div class="doc-sub">{doc_subtitle}</div>
        <div class="stamp">{status_label}</div>
      </div>
    </div>

    <div class="body">
      <div class="meta-grid">
        <div>
          <div class="label">Billed To / Ditagihkan Kepada</div>
          <div class="val">{safe_name}</div>
          <div style="color:#475569; margin-top:2px;">{safe_email}</div>
        </div>
        <div style="text-align:right;">
          <div class="label">Reference / Order ID</div>
          <div class="val" style="font-family:monospace;">{safe_order}</div>
          <div class="label" style="margin-top:10px;">Issue Date / Tanggal Terbit</div>
          <div class="val">{date_str}</div>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Description / Keterangan Layanan</th>
            <th class="num">Qty</th>
            <th class="num">Amount (IDR)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>{item_desc}</strong></td>
            <td class="num">1</td>
            <td class="num">{amount_prefix}{_fmt_idr(amount)}</td>
          </tr>
        </tbody>
      </table>

      <div class="totals">
        <div class="totals-row">
          <span style="color:#64748b;">Subtotal</span>
          <span>{amount_prefix}{_fmt_idr(amount)}</span>
        </div>
        <div class="totals-row">
          <span style="color:#64748b;">Tax / PPN (Included)</span>
          <span>Rp 0</span>
        </div>
        <div class="totals-row totals-final">
          <span>{total_label}</span>
          <span>{amount_prefix}{_fmt_idr(amount)}</span>
        </div>
      </div>

      <div class="sig-box">
        <div style="color:#475569;">
          <strong>Verification Hash:</strong> {safe_order}<br />
          <strong>Payment Gateway:</strong> {"Internal Proration Ledger" if is_downgrade else "Midtrans Snap"}
        </div>
        <div class="sig-line">
          <strong>Authorized Billing System</strong><br />
          <span style="color:#64748b;">PT False Speech Teknologi Indonesia</span>
        </div>
      </div>

      <div class="footer">
        <strong>Official Notice:</strong> This electronic document is officially issued by PT False Speech Teknologi Indonesia
        and is legally valid without a wet signature (dokumen ini diterbitkan secara elektronik dan sah tanpa tanda tangan basah).
        Please retain this document for your accounting and subscription audit records.
      </div>
    </div>
  </div>
</body>
</html>"""


def generate_invoice_pdf(
    user_name: str,
    order_id: str,
    amount: int,
    tier: str,
    user_email: str = "",
    is_downgrade: bool = False,
    previous_tier: Optional[str] = None,
    issued_at: Optional[datetime] = None,
) -> bytes:
    """Generates a formal downloadable A4 PDF invoice or downgrade credit note."""
    dt = issued_at or datetime.now(timezone.utc)
    date_str = dt.strftime("%d %B %Y, %H:%M UTC")
    tier_display = TIER_NAMES.get(tier, tier.replace("_", " ").title())
    prev_display = TIER_NAMES.get(previous_tier or "", (previous_tier or "").replace("_", " ").title())

    doc_title = "OFFICIAL CREDIT NOTE" if is_downgrade else "OFFICIAL PAYMENT INVOICE"
    doc_sub = (
        "NOTA PENYESUAIAN & KOMPENSASI PAKET LANGGANAN"
        if is_downgrade
        else "FAKTUR RESMI PEMBAYARAN LANGGANAN"
    )
    status_label = "CREDITED / PENYESUAIAN" if is_downgrade else "PAID / LUNAS"
    item_desc = (
        f"Plan Downgrade ({prev_display} -> {tier_display}) - Prorated Balance Credit"
        if is_downgrade
        else f"False Speech Subscription - {tier_display}"
    )
    amount_prefix = "+" if is_downgrade else ""
    total_label = "Total Credited to Balance" if is_downgrade else "Total Amount Paid"

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Header banner (#202734)
    pdf.set_fill_color(32, 39, 52)
    pdf.rect(0, 0, 210, 40, style="F")

    pdf.set_xy(15, 10)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(183, 216, 148)  # #B7D894 brand-green
    pdf.cell(95, 9, "FALSE SPEECH", ln=0)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(85, 9, doc_title, align="R", ln=1)

    pdf.set_x(15)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(203, 213, 225)
    pdf.cell(95, 5, "PT False Speech Teknologi Indonesia", ln=0)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(85, 5, doc_sub, align="R", ln=1)

    pdf.set_x(15)
    pdf.cell(95, 5, "Real-Time AI Voice Verification Platform | billing@falsespeech.app", ln=0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(183, 216, 148)
    pdf.cell(85, 5, f"STATUS: {status_label}", align="R", ln=1)

    # Customer & Reference metadata
    pdf.ln(14)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(95, 5, "BILLED TO / DITAGIHKAN KEPADA", ln=0)
    pdf.cell(85, 5, "REFERENCE / ORDER ID", align="R", ln=1)

    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(95, 6, (user_name or "Valued Customer")[:60], ln=0)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(85, 6, order_id, align="R", ln=1)

    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(95, 5, (user_email or "-")[:60], ln=0)
    pdf.cell(85, 5, f"Issued: {date_str}", align="R", ln=1)

    pdf.ln(8)
    pdf.set_draw_color(203, 213, 225)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(8)

    # Itemized Table Header
    pdf.set_fill_color(248, 250, 252)
    pdf.set_text_color(71, 85, 105)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(120, 9, "  DESCRIPTION / KETERANGAN LAYANAN", border=1, fill=True)
    pdf.cell(20, 9, "QTY", border=1, align="C", fill=True)
    pdf.cell(40, 9, "AMOUNT (IDR)  ", border=1, align="R", fill=True, ln=1)

    # Itemized Table Row
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.cell(120, 11, f"  {item_desc[:68]}", border=1)
    pdf.cell(20, 11, "1", border=1, align="C")
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(40, 11, f"{amount_prefix}{_fmt_idr(amount)}  ", border=1, align="R", ln=1)

    # Totals block
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(120, 6, "")
    pdf.cell(25, 6, "Subtotal:", align="R")
    pdf.cell(35, 6, f"{amount_prefix}{_fmt_idr(amount)}", align="R", ln=1)

    pdf.cell(120, 6, "")
    pdf.cell(25, 6, "PPN (Incl.):", align="R")
    pdf.cell(35, 6, "Rp 0", align="R", ln=1)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(32, 39, 52)
    pdf.cell(100, 9, "")
    pdf.cell(45, 9, f"{total_label}:", border="T", align="R")
    pdf.cell(35, 9, f"{amount_prefix}{_fmt_idr(amount)}", border="T", align="R", ln=1)

    # Official Verification & Signature Block
    pdf.ln(18)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(71, 85, 105)
    gateway = "Internal Proration Ledger" if is_downgrade else "Midtrans Snap Gateway"
    pdf.cell(110, 5, f"Payment Channel: {gateway}", ln=0)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(70, 5, "Authorized Billing System", align="C", ln=1)

    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(110, 5, f"Document Verification ID: {order_id}", ln=0)
    pdf.cell(70, 5, "PT False Speech Teknologi Indonesia", align="C", ln=1)

    # Legal Disclaimer Footer
    pdf.ln(14)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(
        180,
        4.5,
        "OFFICIAL NOTICE: This electronic document is officially issued by PT False Speech Teknologi Indonesia "
        "and is legally valid without a wet signature (dokumen ini diterbitkan secara elektronik oleh sistem "
        "dan sah tanpa tanda tangan basah). Please retain this PDF for your financial and subscription records.",
    )

    return bytes(pdf.output())
