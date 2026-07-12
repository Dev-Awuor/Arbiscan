"""
Report collection + traceable PDF generation.

A Report freezes the current arbs into an immutable, sized snapshot and seals
it with a SHA-256 content hash and an HMAC-SHA256 signature (keyed by
SECRET_KEY). The generated PDF embeds a QR code carrying the report id, UTC
timestamp, hash and signature - so any printout can be verified as genuinely
produced by this system at a specific time.
"""
import hashlib
import hmac
import io
import json
import os
from datetime import timezone

from django.conf import settings

MARKET_LEGS = {
    "FT_1X2": ["Home", "Draw", "Away"], "H2H": ["Home", "Away"],
    "BTTS": ["Yes", "No"], "OU25": ["Over", "Under"],
    "OU15": ["Over", "Under"], "OU35": ["Over", "Under"],
    "DC": ["1X", "X2", "12"],
}


def _to_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return list(v.values())
    return [v]


def _legs_for(arb, n):
    if arb.market == "H2H":
        return [arb.fixture.home_team, arb.fixture.away_team]
    return MARKET_LEGS.get(arb.market, [f"Leg{i+1}" for i in range(n)])


def size_arb(arb, target: float):
    """Scale a stored arb so this match alone yields `target` profit."""
    profit = float(arb.profit)
    if profit <= 0:
        return None
    scale  = target / profit
    odds   = [float(o) for o in _to_list(arb.odds)]
    stakes = [round(float(s) * scale, 2) for s in _to_list(arb.stakes)]
    books  = _to_list(arb.books)
    legs   = _legs_for(arb, len(odds))
    rows   = []
    for i in range(len(odds)):
        rows.append({
            "label": str(legs[i]) if i < len(legs) else f"Leg{i+1}",
            "book":  str(books[i]).upper() if i < len(books) else "?",
            "odds":  round(odds[i], 3),
            "stake": stakes[i] if i < len(stakes) else 0.0,
        })
    return {
        "match":      str(arb.fixture),
        "market":     arb.market,
        "kickoff":    arb.fixture.kickoff.isoformat() if arb.fixture.kickoff else "",
        "margin_pct": round(float(arb.profit_pct), 3),
        "legs":       rows,
        "bankroll":   round(sum(stakes), 2),
        "profit":     round(float(target), 2),
    }


def build_snapshot(arbs, target: float):
    snap = []
    rank = 1
    for arb in arbs:
        if float(arb.profit_pct) <= 0:
            continue
        row = size_arb(arb, target)
        if row:
            row["rank"] = rank
            snap.append(row)
            rank += 1
    return snap


# ----- sealing / verification -------------------------------------------

def _canonical(snapshot) -> str:
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)


def _sig_message(report) -> str:
    return f"{report.report_id}|{report.created_at.isoformat()}|{report.content_hash}"


def seal(report):
    """Compute content hash + signature. Requires report.created_at set (saved)."""
    report.content_hash = hashlib.sha256(_canonical(report.snapshot).encode()).hexdigest()
    report.signature = hmac.new(
        settings.SECRET_KEY.encode(), _sig_message(report).encode(), hashlib.sha256
    ).hexdigest()
    return report


def verify(report) -> bool:
    """True iff the snapshot is unmodified and the signature is ours."""
    if hashlib.sha256(_canonical(report.snapshot).encode()).hexdigest() != report.content_hash:
        return False
    expected = hmac.new(
        settings.SECRET_KEY.encode(), _sig_message(report).encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, report.signature)


def qr_payload(report) -> dict:
    return {
        "sys": "ARBISCAN",
        "rid": str(report.report_id),
        "ts":  report.created_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n":   report.arb_count,
        "sha": report.content_hash,
        "sig": report.signature,
    }


# ----- PDF rendering ----------------------------------------------------

def render_pdf(report, out_dir=None) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    import qrcode

    out_dir = out_dir or os.path.join(str(settings.BASE_DIR), "reports")
    os.makedirs(out_dir, exist_ok=True)
    utc      = report.created_at.astimezone(timezone.utc)
    ts_file  = utc.strftime("%Y%m%d-%H%M%S")
    ts_human = utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    path     = os.path.join(out_dir, f"ARBISCAN_{ts_file}_{report.short_id}.pdf")

    # QR with full traceability payload
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(json.dumps(qr_payload(report), separators=(",", ":")))
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    buf.seek(0)
    qr_reader = ImageReader(buf)

    NAVY = colors.HexColor("#0b2545"); GREEN = colors.HexColor("#1b7a43")
    LIGHT = colors.HexColor("#eef2f7"); GREY = colors.HexColor("#666666")
    styles = getSampleStyleSheet()
    h1   = ParagraphStyle("h1", parent=styles["Title"], textColor=NAVY, fontSize=20, spaceAfter=2)
    sub  = ParagraphStyle("sub", parent=styles["Normal"], textColor=GREY, fontSize=9)
    cardh= ParagraphStyle("cardh", parent=styles["Heading3"], textColor=NAVY, fontSize=11, spaceBefore=8, spaceAfter=2)
    note = ParagraphStyle("note", parent=styles["Normal"], textColor=GREY, fontSize=7.5, leading=10)

    flow = []
    flow.append(Paragraph("ARBISCAN", h1))
    flow.append(Paragraph("Arbitrage Action Report &mdash; cross-book guaranteed-return betting", sub))
    flow.append(Spacer(1, 4))
    flow.append(HRFlowable(width="100%", thickness=1.2, color=NAVY))
    flow.append(Spacer(1, 6))

    meta = [
        ["Sport",   report.sport or "-",            "Generated", ts_human],
        ["Market",  report.market or "-",           "Report ID", report.short_id],
        ["Target/match", f"KES {float(report.target):,.0f}", "Arbs", str(report.arb_count)],
        ["Books",   ", ".join(report.books) or "-", "Total profit", f"KES {float(report.total_profit):,.2f}"],
    ]
    mt = Table(meta, colWidths=[26*mm, 60*mm, 26*mm, 60*mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), LIGHT), ("BACKGROUND", (2,0), (2,-1), LIGHT),
        ("TEXTCOLOR", (0,0), (0,-1), NAVY),   ("TEXTCOLOR", (2,0), (2,-1), NAVY),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5), ("GRID", (0,0), (-1,-1), 0.4, colors.white),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    flow.append(mt)
    flow.append(Spacer(1, 8))

    if not report.snapshot:
        flow.append(Paragraph("No arbitrage opportunities in this run.", styles["Normal"]))
    else:
        # Summary table
        head = ["#", "Match", "Margin", "Bankroll (KES)", "Profit (KES)"]
        data = [head]
        for r in report.snapshot:
            data.append([str(r["rank"]), r["match"], f"+{r['margin_pct']:.3f}%",
                         f"{r['bankroll']:,.2f}", f"{r['profit']:,.2f}"])
        st = Table(data, colWidths=[8*mm, 86*mm, 22*mm, 32*mm, 28*mm], repeatRows=1)
        st.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT]),
            ("TEXTCOLOR", (4,1), (4,-1), GREEN), ("FONTNAME", (4,1), (4,-1), "Helvetica-Bold"),
            ("ALIGN", (2,0), (-1,-1), "RIGHT"), ("ALIGN", (0,0), (0,-1), "CENTER"),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cfd8e3")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        flow.append(st)
        flow.append(Spacer(1, 6))
        flow.append(Paragraph("ACTION CARDS", cardh))

        # Per-arb action cards
        for r in report.snapshot:
            flow.append(Paragraph(f"#{r['rank']}  {r['match']}", cardh))
            legrows = [["Stake (KES)", "Selection", "Odds", "Bookmaker"]]
            for leg in r["legs"]:
                legrows.append([f"{leg['stake']:,.2f}", leg["label"],
                                f"{leg['odds']:.3f}", leg["book"]])
            legrows.append(["", "GUARANTEED PROFIT",
                            f"+{r['margin_pct']:.3f}%", f"KES {r['profit']:,.2f}"])
            lt = Table(legrows, colWidths=[30*mm, 86*mm, 22*mm, 38*mm])
            lt.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#d7e3f0")),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 8),
                ("FONTNAME", (0,1), (0,-2), "Helvetica-Bold"),
                ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#e7f4ec")),
                ("TEXTCOLOR", (0,-1), (-1,-1), GREEN), ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
                ("ALIGN", (0,0), (0,-1), "RIGHT"), ("ALIGN", (2,0), (2,-1), "CENTER"),
                ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cfd8e3")),
                ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            flow.append(lt)

    flow.append(Spacer(1, 10))
    flow.append(Paragraph(
        "Odds move continuously; verify each price at the bookmaker before staking. "
        "Stake both legs promptly to lock the margin. Figures assume both legs are accepted "
        "in full. This document is auto-generated; authenticity is provable via the QR code "
        "and HMAC-SHA256 signature in the footer.", note))

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#cfd8e3"))
        canvas.line(15*mm, 34*mm, A4[0]-15*mm, 34*mm)
        size = 26*mm
        canvas.drawImage(qr_reader, A4[0]-size-15*mm, 6*mm, size, size, mask="auto")
        canvas.setFont("Helvetica-Bold", 7); canvas.setFillColor(NAVY)
        canvas.drawString(15*mm, 30*mm, "TRACEABILITY  (scan QR to verify)")
        canvas.setFont("Helvetica", 6); canvas.setFillColor(GREY)
        canvas.drawString(15*mm, 26*mm, f"System    : ARBISCAN")
        canvas.drawString(15*mm, 23*mm, f"Report ID : {report.report_id}")
        canvas.drawString(15*mm, 20*mm, f"Generated : {ts_human}")
        canvas.drawString(15*mm, 17*mm, f"SHA-256   : {report.content_hash}")
        canvas.drawString(15*mm, 14*mm, f"Signature : {report.signature[:48]}...")
        canvas.drawString(15*mm, 11*mm, "Verify: python manage.py verify_report --id <Report ID>")
        canvas.setFont("Helvetica", 6)
        canvas.drawRightString(A4[0]-15*mm, 6*mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=38*mm,
                            title=f"ARBISCAN Report {report.short_id}",
                            author="ARBISCAN")
    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)
    return path
