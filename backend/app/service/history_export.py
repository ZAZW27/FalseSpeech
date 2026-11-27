import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF


def _safe_ascii(text: Any) -> str:
    """Sanitize text for standard Helvetica PDF font."""
    s = str(text or "")
    return s.encode("latin-1", "replace").decode("latin-1")


def _fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "-"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _fmt_dur(seconds: float | int) -> str:
    s = max(0, int(round(float(seconds or 0))))
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {sec}s"
    if m:
        return f"{m}m {sec}s"
    return f"{sec}s"


def _session_label(row) -> str:
    return (row.title or "").strip() or f"Session #{row.id}"


def export_history_csv(items: list[tuple[Any, list[Any]]], user_name: str, user_email: str) -> bytes:
    """Export sessions & chunks as UTF-8 BOM CSV (Excel/ATS-ready)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Session ID",
            "Session Title",
            "Source",
            "Session Started (UTC)",
            "Session Duration (s)",
            "Session Verdict",
            "Session Avg Fake %",
            "HR Notes",
            "Chunk #",
            "Chunk Recorded (UTC)",
            "Chunk Duration (s)",
            "Chunk Verdict",
            "Fake Probability %",
            "Real Probability %",
        ]
    )
    for row, segs in items:
        title = _session_label(row)
        notes = (row.notes or "").replace("\n", " ").strip()
        avg_pct = round(float(row.avg_fake_prob or 0.0) * 100, 2)
        if not segs:
            writer.writerow(
                [
                    row.id,
                    title,
                    row.source or "web",
                    _fmt_dt(row.started_at),
                    int(row.duration_s or 0),
                    (row.verdict or "real").upper(),
                    avg_pct,
                    notes,
                    "-",
                    "-",
                    0,
                    "-",
                    "-",
                    "-",
                ]
            )
            continue
        for seg in segs:
            writer.writerow(
                [
                    row.id,
                    title,
                    row.source or "web",
                    _fmt_dt(row.started_at),
                    int(row.duration_s or 0),
                    (row.verdict or "real").upper(),
                    avg_pct,
                    notes,
                    seg.offset_s,
                    _fmt_dt(getattr(seg, "recorded_at", None) or row.started_at),
                    round(float(getattr(seg, "duration_s", 0.0) or 0.0), 2),
                    "AI / FAKE" if seg.is_fake else "HUMAN / REAL",
                    round(float(seg.fake_prob or 0.0) * 100, 2),
                    round(float(seg.real_prob or 0.0) * 100, 2),
                ]
            )
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def export_history_json(items: list[tuple[Any, list[Any]]], user_name: str, user_email: str) -> bytes:
    """Export sessions & chunks as structured JSON for HRIS/ATS systems."""
    payload = {
        "report": "False Speech Voice Verification Report",
        "generated_at": _fmt_dt(datetime.now(timezone.utc)),
        "account": {"name": user_name, "email": user_email},
        "total_sessions": len(items),
        "sessions": [
            {
                "session_id": str(row.id),
                "title": _session_label(row),
                "notes": row.notes or "",
                "source": row.source or "web",
                "started_at": _fmt_dt(row.started_at),
                "ended_at": _fmt_dt(row.ended_at),
                "duration_seconds": int(row.duration_s or 0),
                "verdict": row.verdict,
                "avg_fake_prob": round(float(row.avg_fake_prob or 0.0), 4),
                "fake_chunks": int(row.fake_count or 0),
                "real_chunks": int(row.real_count or 0),
                "chunks": [
                    {
                        "chunk_index": seg.offset_s,
                        "recorded_at": _fmt_dt(getattr(seg, "recorded_at", None) or row.started_at),
                        "duration_s": round(float(getattr(seg, "duration_s", 0.0) or 0.0), 2),
                        "is_fake": bool(seg.is_fake),
                        "verdict": "fake" if seg.is_fake else "real",
                        "fake_prob": round(float(seg.fake_prob or 0.0), 4),
                        "real_prob": round(float(seg.real_prob or 0.0), 4),
                    }
                    for seg in segs
                ],
            }
            for row, segs in items
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def export_history_txt(items: list[tuple[Any, list[Any]]], user_name: str, user_email: str) -> bytes:
    """Export clean plain-text HR audit memo."""
    total_chunks = sum(len(segs) for _, segs in items)
    total_fake = sum(int(r.fake_count or 0) for r, _ in items)
    total_real = sum(int(r.real_count or 0) for r, _ in items)
    lines = [
        "========================================================================",
        "FALSE SPEECH - HR VOICE VERIFICATION AUDIT REPORT",
        "========================================================================",
        f"Generated At : {_fmt_dt(datetime.now(timezone.utc))}",
        f"Prepared For : {user_name} <{user_email}>",
        f"Summary      : {len(items)} Session(s) | {total_chunks} Chunk(s) | {total_fake} AI Flagged | {total_real} Human Verified",
        "========================================================================",
        "",
    ]
    for row, segs in items:
        avg_pct = round(float(row.avg_fake_prob or 0.0) * 100, 1)
        lines.append(f"[{_session_label(row)}] (ID: #{row.id})")
        lines.append(
            f"  Date     : {_fmt_dt(row.started_at)}  |  Duration: {_fmt_dur(row.duration_s)}  |  Source: {(row.source or 'web').upper()}"
        )
        lines.append(
            f"  Verdict  : {(row.verdict or 'real').upper()}  |  Avg AI Risk: {avg_pct}%  |  Chunks: {len(segs)} ({row.fake_count} AI / {row.real_count} Human)"
        )
        if row.notes:
            lines.append(f"  HR Notes : {row.notes.strip()}")
        if segs:
            lines.append("  Chunks   :")
            for seg in segs:
                label = "AI/FAKE " if seg.is_fake else "HUMAN   "
                f_pct = round(float(seg.fake_prob or 0.0) * 100, 1)
                r_pct = round(float(seg.real_prob or 0.0) * 100, 1)
                rec = _fmt_dt(getattr(seg, "recorded_at", None) or row.started_at)
                lines.append(
                    f"    - Chunk #{seg.offset_s:<3} | {rec} | {label} | Fake: {f_pct:5.1f}% | Real: {r_pct:5.1f}%"
                )
        lines.append("------------------------------------------------------------------------")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def export_history_md(items: list[tuple[Any, list[Any]]], user_name: str, user_email: str) -> bytes:
    """Export Markdown report suitable for Notion, Confluence, Jira, or HR docs."""
    total_chunks = sum(len(segs) for _, segs in items)
    total_fake = sum(int(r.fake_count or 0) for r, _ in items)
    total_real = sum(int(r.real_count or 0) for r, _ in items)
    lines = [
        "# False Speech — HR Voice Verification Report",
        "",
        f"- **Generated:** {_fmt_dt(datetime.now(timezone.utc))}",
        f"- **Account:** {user_name} ({user_email})",
        f"- **Overview:** {len(items)} session(s), {total_chunks} chunk(s), **{total_fake} AI flagged**, **{total_real} human verified**",
        "",
        "---",
        "",
    ]
    for row, segs in items:
        avg_pct = round(float(row.avg_fake_prob or 0.0) * 100, 1)
        lines.append(f"## {_session_label(row)} (`#{row.id}`)")
        lines.append("")
        lines.append(
            f"- **Date:** {_fmt_dt(row.started_at)}  \n"
            f"- **Duration:** {_fmt_dur(row.duration_s)} | **Source:** {(row.source or 'web').upper()}  \n"
            f"- **Verdict:** `{(row.verdict or 'real').upper()}` | **Avg AI Risk:** {avg_pct}% ({row.fake_count} AI / {row.real_count} Human)"
        )
        if row.notes:
            lines.append(f"- **HR Notes:** {row.notes.strip()}")
        lines.append("")
        if segs:
            lines.append("| Chunk # | Recorded (UTC) | Verdict | Fake % | Real % |")
            lines.append("|---:|---|---|---:|---:|")
            for seg in segs:
                label = "AI / Fake" if seg.is_fake else "Human / Real"
                f_pct = round(float(seg.fake_prob or 0.0) * 100, 1)
                r_pct = round(float(seg.real_prob or 0.0) * 100, 1)
                rec = _fmt_dt(getattr(seg, "recorded_at", None) or row.started_at)
                lines.append(f"| #{seg.offset_s} | {rec} | {label} | {f_pct}% | {r_pct}% |")
            lines.append("")
    return "\n".join(lines).encode("utf-8")


def export_history_pdf(items: list[tuple[Any, list[Any]]], user_name: str, user_email: str) -> bytes:
    """Generate a formal A4 PDF HR Voice Verification Audit Report using fpdf2."""
    total_chunks = sum(len(segs) for _, segs in items)
    total_fake = sum(int(r.fake_count or 0) for r, _ in items)
    total_real = sum(int(r.real_count or 0) for r, _ in items)
    avg_all = (
        round(sum(float(r.avg_fake_prob or 0.0) for r, _ in items) / len(items) * 100, 1)
        if items
        else 0.0
    )

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Header banner
    pdf.set_fill_color(32, 39, 52)
    pdf.rect(0, 0, 210, 36, style="F")

    pdf.set_xy(14, 9)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(183, 216, 148)
    pdf.cell(95, 8, "FALSE SPEECH", ln=0)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(87, 8, "VOICE VERIFICATION AUDIT REPORT", align="R", ln=1)

    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(203, 213, 225)
    pdf.cell(95, 5, "Real-Time AI Deepfake Voice Screening for HR & Compliance", ln=0)
    pdf.cell(87, 5, f"Generated: {_fmt_dt(datetime.now(timezone.utc))}", align="R", ln=1)

    pdf.set_x(14)
    pdf.cell(182, 5, _safe_ascii(f"Prepared for: {user_name} ({user_email})"), ln=1)

    # Summary strip
    pdf.ln(10)
    pdf.set_fill_color(244, 247, 252)
    pdf.set_draw_color(203, 213, 225)
    y0 = pdf.get_y()
    pdf.rect(14, y0, 182, 18, style="FD")

    boxes = [
        ("SESSIONS", str(len(items))),
        ("TOTAL CHUNKS", str(total_chunks)),
        ("AI FLAGGED", str(total_fake)),
        ("HUMAN VERIFIED", str(total_real)),
        ("AVG AI RISK", f"{avg_all}%"),
    ]
    col_w = 182 / len(boxes)
    for idx, (label, val) in enumerate(boxes):
        x = 14 + idx * col_w
        pdf.set_xy(x, y0 + 3)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(col_w, 4, label, align="C")
        pdf.set_xy(x, y0 + 8)
        pdf.set_font("Helvetica", "B", 12)
        if label == "AI FLAGGED" and total_fake > 0:
            pdf.set_text_color(200, 45, 65)
        elif label == "HUMAN VERIFIED":
            pdf.set_text_color(21, 128, 61)
        else:
            pdf.set_text_color(15, 23, 42)
        pdf.cell(col_w, 7, val, align="C")

    pdf.set_y(y0 + 24)

    if not items:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(182, 10, "No detection sessions matched the selected filters.", align="C", ln=1)
        return bytes(pdf.output())

    # Per-session sections
    for row, segs in items:
        if pdf.get_y() > 245:
            pdf.add_page()

        avg_pct = round(float(row.avg_fake_prob or 0.0) * 100, 1)
        verdict_up = (row.verdict or "real").upper()

        # Session bar
        pdf.set_fill_color(32, 39, 52)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(125, 8, _safe_ascii(f"  {_session_label(row)} (#{row.id})"), fill=True, ln=0)
        if verdict_up == "FAKE":
            pdf.set_text_color(255, 150, 161)
        elif verdict_up == "MIXED":
            pdf.set_text_color(253, 224, 71)
        else:
            pdf.set_text_color(183, 216, 148)
        pdf.cell(57, 8, f"VERDICT: {verdict_up} ({avg_pct}% AI)  ", align="R", fill=True, ln=1)

        # Metadata line
        pdf.set_fill_color(248, 250, 252)
        pdf.set_text_color(51, 65, 85)
        pdf.set_font("Helvetica", "", 8.5)
        meta_line = (
            f"  Date: {_fmt_dt(row.started_at)}   |   Duration: {_fmt_dur(row.duration_s)}   |   "
            f"Source: {(row.source or 'web').upper()}   |   Chunks: {len(segs)} ({row.fake_count} AI / {row.real_count} Human)"
        )
        pdf.cell(182, 6.5, _safe_ascii(meta_line), border="LRB", fill=True, ln=1)

        if row.notes:
            pdf.set_text_color(30, 41, 59)
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.multi_cell(182, 5.5, _safe_ascii(f"  HR Notes: {row.notes.strip()}"), border="LRB")

        if segs:
            # Chunk table header
            pdf.set_fill_color(226, 232, 240)
            pdf.set_text_color(51, 65, 85)
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(22, 6, "  CHUNK", border=1, fill=True)
            pdf.cell(56, 6, "  RECORDED (UTC)", border=1, fill=True)
            pdf.cell(24, 6, "DURATION", border=1, align="C", fill=True)
            pdf.cell(32, 6, "VERDICT", border=1, align="C", fill=True)
            pdf.cell(24, 6, "FAKE %", border=1, align="R", fill=True)
            pdf.cell(24, 6, "REAL %  ", border=1, align="R", fill=True, ln=1)

            pdf.set_font("Helvetica", "", 8)
            for seg in segs:
                if pdf.get_y() > 272:
                    pdf.add_page()
                f_pct = round(float(seg.fake_prob or 0.0) * 100, 1)
                r_pct = round(float(seg.real_prob or 0.0) * 100, 1)
                rec = _fmt_dt(getattr(seg, "recorded_at", None) or row.started_at)
                dur_s = round(float(getattr(seg, "duration_s", 0.0) or 0.0), 1)
                pdf.set_text_color(15, 23, 42)
                pdf.cell(22, 5.8, f"  #{seg.offset_s}", border=1)
                pdf.cell(56, 5.8, f"  {rec}", border=1)
                pdf.cell(24, 5.8, f"{dur_s}s" if dur_s > 0 else "-", border=1, align="C")
                if seg.is_fake:
                    pdf.set_text_color(190, 24, 50)
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.cell(32, 5.8, "AI / FAKE", border=1, align="C")
                else:
                    pdf.set_text_color(21, 128, 61)
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.cell(32, 5.8, "HUMAN / REAL", border=1, align="C")
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(15, 23, 42)
                pdf.cell(24, 5.8, f"{f_pct}%", border=1, align="R")
                pdf.cell(24, 5.8, f"{r_pct}%  ", border=1, align="R", ln=1)

        pdf.ln(5)

    # Footer note
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(
        182,
        4,
        "CONFIDENTIAL HR RECORD: Generated by False Speech AI Voice Verification Platform. "
        "Zero raw audio is retained on disk; only inference metadata and statistical scores are recorded.",
    )
    return bytes(pdf.output())
