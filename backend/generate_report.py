"""
generate_report.py

Generates a professional PDF report from test_result.json.
Run from anywhere:
    python3 /path/to/backend/generate_report.py

Output: backend/contract_analysis_report.pdf
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Load result ──────────────────────────────────────────────────────────────
RESULT_PATH = SCRIPT_DIR / "test_result.json"
OUTPUT_PATH = SCRIPT_DIR / "contract_analysis_report.pdf"

with open(RESULT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

clauses = data["clauses"]
gemini_summary = data.get("gemini_summary", {})

# ── Colour palette ───────────────────────────────────────────────────────────
BRAND_DARK   = colors.HexColor("#0F172A")   # deep navy
BRAND_BLUE   = colors.HexColor("#1E40AF")   # royal blue
BRAND_LIGHT  = colors.HexColor("#EFF6FF")   # pale blue bg
BRAND_ACCENT = colors.HexColor("#3B82F6")   # bright blue

GREEN   = colors.HexColor("#16A34A")
GREEN_L = colors.HexColor("#DCFCE7")
AMBER   = colors.HexColor("#D97706")
AMBER_L = colors.HexColor("#FEF3C7")
RED     = colors.HexColor("#DC2626")
RED_L   = colors.HexColor("#FEE2E2")
BLUE    = colors.HexColor("#2563EB")
BLUE_L  = colors.HexColor("#DBEAFE")
GREY    = colors.HexColor("#6B7280")
GREY_L  = colors.HexColor("#F9FAFB")
WHITE   = colors.white
BLACK   = colors.HexColor("#1F2937")

# ── Styles ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    """Create a named ParagraphStyle."""
    return ParagraphStyle(name, **kw)

H1 = S("H1", fontSize=26, leading=32, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
H2 = S("H2", fontSize=16, leading=20, textColor=BRAND_DARK,
        fontName="Helvetica-Bold", spaceAfter=4)
H3 = S("H3", fontSize=12, leading=16, textColor=BRAND_BLUE,
        fontName="Helvetica-Bold", spaceAfter=2)
BODY = S("BODY", fontSize=9, leading=13, textColor=BLACK,
         fontName="Helvetica")
SMALL = S("SMALL", fontSize=8, leading=11, textColor=GREY,
          fontName="Helvetica")
CAPTION = S("CAPTION", fontSize=8, leading=10, textColor=GREY,
            fontName="Helvetica", alignment=TA_CENTER)
CELL = S("CELL", fontSize=8, leading=10, textColor=BLACK,
         fontName="Helvetica", wordWrap="CJK")
CELL_B = S("CELL_B", fontSize=8, leading=10, textColor=BLACK,
           fontName="Helvetica-Bold", wordWrap="CJK")
HDR = S("HDR", fontSize=8, leading=10, textColor=WHITE,
        fontName="Helvetica-Bold", alignment=TA_CENTER)

# ── Helpers ──────────────────────────────────────────────────────────────────
def status_color(status):
    mapping = {
        "present": (GREEN_L, GREEN),
        "present_fuzzy": (BLUE_L, BLUE),
        "truly_missing": (RED_L, RED),
        "needs_review": (AMBER_L, AMBER),
        "confirmed_present": (GREEN_L, GREEN),
        "confirmed_missing": (RED_L, RED),
        "partially_supported": (BLUE_L, BLUE),
        "not_supported": (RED_L, RED),
    }
    return mapping.get(str(status).lower(), (GREY_L, GREY))

def risk_color(risk):
    return {
        "HIGH": (RED_L, RED),
        "MEDIUM": (AMBER_L, AMBER),
        "LOW": (GREEN_L, GREEN),
    }.get(str(risk).upper(), (GREY_L, GREY))

def pill(text, bg, fg):
    return Paragraph(
        f'<font color="{fg.hexval()}">{text}</font>',
        ParagraphStyle("pill", fontSize=7, leading=9, fontName="Helvetica-Bold",
                       backColor=bg, borderPadding=(2, 4, 2, 4), alignment=TA_CENTER)
    )

def HR():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E5E7EB"),
                      spaceAfter=6, spaceBefore=6)

def section_title(text):
    return [
        Spacer(1, 10),
        Paragraph(text, H2),
        HRFlowable(width="100%", thickness=2, color=BRAND_ACCENT,
                   spaceAfter=8, spaceBefore=2),
    ]

# ── Aggregate data ───────────────────────────────────────────────────────────
found_count   = data.get("found_count", 0)
missing_count = data.get("missing_count", 0)
review_count  = data.get("needs_review_count", 0)
total         = data.get("total_gcc_clauses", len(clauses))
pages         = data.get("page_count", "—")
filename      = data.get("filename", "Contract PDF")

# Status breakdown
status_counts = {}
for c in clauses:
    s = c.get("final_status") or c.get("status", "unknown")
    status_counts[s] = status_counts.get(s, 0) + 1

# Risk breakdown by final status
risk_matrix = {}
for c in clauses:
    risk = c.get("risk_category", "UNKNOWN")
    st   = c.get("final_status") or c.get("status", "unknown")
    risk_matrix.setdefault(risk, {})
    risk_matrix[risk][st] = risk_matrix[risk].get(st, 0) + 1

# Gemini validation counts
gemini_counts = gemini_summary.get("status_counts", {})

# ── Document setup ───────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    str(OUTPUT_PATH),
    pagesize=A4,
    rightMargin=18*mm,
    leftMargin=18*mm,
    topMargin=18*mm,
    bottomMargin=18*mm,
    title="Railway Contract GCC Analysis Report",
    author="Clauset AI",
)

story = []
W = A4[0] - 36*mm   # usable width

# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Cover / Header
# ════════════════════════════════════════════════════════════════════════════

# Cover banner
banner_data = [[Paragraph("Railway Contract<br/>GCC Compliance Report", H1)]]
banner = Table(banner_data, colWidths=[W])
banner.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), BRAND_DARK),
    ("TOPPADDING",    (0, 0), (-1, -1), 28),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 28),
    ("LEFTPADDING",   (0, 0), (-1, -1), 20),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ("ROUNDEDCORNERS", [6]),
]))
story.append(banner)
story.append(Spacer(1, 12))

# Meta info row
meta_style = ParagraphStyle("meta", fontSize=9, leading=13, textColor=GREY,
                             fontName="Helvetica")
meta_bold  = ParagraphStyle("meta_b", fontSize=9, leading=13, textColor=BLACK,
                              fontName="Helvetica-Bold")
now = datetime.now().strftime("%d %B %Y, %I:%M %p")
meta_rows = [
    [Paragraph("Document", meta_style), Paragraph(filename, meta_bold),
     Paragraph("Report Date", meta_style), Paragraph(now, meta_bold)],
    [Paragraph("Pages Analysed", meta_style), Paragraph(str(pages), meta_bold),
     Paragraph("GCC Clauses Checked", meta_style), Paragraph(str(total), meta_bold)],
    [Paragraph("AI Model", meta_style), Paragraph("Google Gemini (flash-lite)", meta_bold),
     Paragraph("Validation", meta_style), Paragraph("Gemini Second-Pass (2 batches)", meta_bold)],
]
meta_tbl = Table(meta_rows, colWidths=[W*0.18, W*0.32, W*0.18, W*0.32])
meta_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
    ("TOPPADDING",    (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#BFDBFE")),
    ("ROUNDEDCORNERS", [4]),
]))
story.append(meta_tbl)
story.append(Spacer(1, 16))

# ── KPI Cards ────────────────────────────────────────────────────────────────
story += section_title("Executive Summary")

pct_found   = round(found_count / total * 100) if total else 0
pct_missing = round(missing_count / total * 100) if total else 0
pct_review  = round(review_count / total * 100) if total else 0

kpi_items = [
    (str(found_count),   f"{pct_found}% of total",   "Clauses Present",    GREEN,  GREEN_L),
    (str(missing_count), f"{pct_missing}% of total",  "Clauses Missing",    RED,    RED_L),
    (str(review_count),  f"{pct_review}% of total",   "Needs Review",       AMBER,  AMBER_L),
    (str(total),         f"{pages} pages scanned",     "Total GCC Clauses",  BLUE,   BLUE_L),
]

kpi_cells = []
for val, sub, label, fg, bg in kpi_items:
    cell = Table(
        [[Paragraph(f'<font color="{fg.hexval()}" size="22"><b>{val}</b></font>', 
                    ParagraphStyle("kv", fontSize=22, leading=26, fontName="Helvetica-Bold",
                                   textColor=fg, alignment=TA_CENTER))],
         [Paragraph(sub, CAPTION)],
         [Paragraph(label, ParagraphStyle("klabel", fontSize=8, leading=10, 
                                          fontName="Helvetica-Bold", textColor=fg,
                                          alignment=TA_CENTER))]],
        colWidths=[(W - 9*mm) / 4],
    )
    cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [6]),
    ]))
    kpi_cells.append(cell)

kpi_row = Table([kpi_cells], colWidths=[(W - 9*mm) / 4] * 4,
                spaceBefore=0, spaceAfter=16)
kpi_row.setStyle(TableStyle([("LEFTPADDING", (0,0),(-1,-1), 3),
                               ("RIGHTPADDING", (0,0),(-1,-1), 3)]))
story.append(kpi_row)

# ── Status Breakdown Table ────────────────────────────────────────────────────
story += section_title("Clause Status Breakdown")

status_label_map = {
    "present":         "Directly Mapped (Gemini)",
    "present_fuzzy":   "Fuzzy Match (keyword fallback)",
    "truly_missing":   "Truly Missing",
    "needs_review":    "Needs Human Review",
    "unknown":         "Unknown",
}

rows = [[Paragraph(h, HDR) for h in ["Status", "Label", "Count", "% of Total"]]]
rows[0][2] = Paragraph("Count", ParagraphStyle("hdr_r", fontSize=8, leading=10,
                                               textColor=WHITE, fontName="Helvetica-Bold",
                                               alignment=TA_RIGHT))
rows[0][3] = Paragraph("% of Total", ParagraphStyle("hdr_r2", fontSize=8, leading=10,
                                                    textColor=WHITE, fontName="Helvetica-Bold",
                                                    alignment=TA_RIGHT))

style_list = [
    ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
    ("TOPPADDING",    (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_L]),
    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E5E7EB")),
    ("LINEBELOW", (0, -1), (-1, -1), 1, BRAND_ACCENT),
]

for i, (st, cnt) in enumerate(sorted(status_counts.items(),
                                      key=lambda x: -x[1]), start=1):
    bg, fg = status_color(st)
    pct = f"{round(cnt/total*100)}%" if total else "0%"
    rows.append([
        pill(st.replace("_", " ").title(), bg, fg),
        Paragraph(status_label_map.get(st, st), CELL),
        Paragraph(str(cnt), ParagraphStyle("r", fontSize=8, leading=10,
                                            fontName="Helvetica-Bold",
                                            alignment=TA_RIGHT, textColor=fg)),
        Paragraph(pct, ParagraphStyle("r2", fontSize=8, leading=10,
                                       fontName="Helvetica",
                                       alignment=TA_RIGHT, textColor=GREY)),
    ])

sb_tbl = Table(rows, colWidths=[W*0.22, W*0.48, W*0.14, W*0.16])
sb_tbl.setStyle(TableStyle(style_list))
story.append(sb_tbl)
story.append(Spacer(1, 16))

# ── Risk Category Matrix ──────────────────────────────────────────────────────
story += section_title("Risk Category Analysis")

risk_order = ["HIGH", "MEDIUM", "LOW"]
stat_order  = ["present", "present_fuzzy", "truly_missing", "needs_review"]
stat_labels = {
    "present":       "Present",
    "present_fuzzy": "Fuzzy",
    "truly_missing": "Missing",
    "needs_review":  "Review",
}

hdr_row = [Paragraph("Risk", HDR)] + \
          [Paragraph(stat_labels[s], HDR) for s in stat_order] + \
          [Paragraph("Total", HDR)]

risk_rows = [hdr_row]
for risk in risk_order:
    counts = risk_matrix.get(risk, {})
    row_total = sum(counts.values())
    rbg, rfg = risk_color(risk)
    row = [pill(risk, rbg, rfg)]
    for st in stat_order:
        n = counts.get(st, 0)
        _, fg = status_color(st)
        row.append(Paragraph(
            str(n) if n else "—",
            ParagraphStyle("rc", fontSize=9, leading=11, fontName="Helvetica-Bold",
                           textColor=fg if n else GREY, alignment=TA_CENTER)
        ))
    row.append(Paragraph(str(row_total), ParagraphStyle("rt", fontSize=9, leading=11,
                          fontName="Helvetica-Bold", textColor=BLACK, alignment=TA_CENTER)))
    risk_rows.append(row)

risk_tbl = Table(risk_rows,
                 colWidths=[W*0.12, W*0.18, W*0.18, W*0.18, W*0.18, W*0.16])
risk_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
    ("TOPPADDING",    (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN",  (1, 0), (-1, -1), "CENTER"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_L]),
    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E5E7EB")),
    ("LINEBELOW", (0, -1), (-1, -1), 1, BRAND_ACCENT),
]))
story.append(risk_tbl)
story.append(Spacer(1, 16))

# ── Gemini Validation Summary ─────────────────────────────────────────────────
story += section_title("Gemini AI Second-Pass Validation")

gemini_label_map = {
    "confirmed_present":   ("Confirmed Present",    GREEN_L, GREEN),
    "partially_supported": ("Partially Supported",  BLUE_L,  BLUE),
    "not_supported":       ("Not Supported",         RED_L,   RED),
    "confirmed_missing":   ("Confirmed Missing",     RED_L,   RED),
    "needs_review":        ("Needs Review",          AMBER_L, AMBER),
}

g_rows = [[Paragraph(h, HDR) for h in ["Gemini Verdict", "Count", "Description"]]]
for st, cnt in sorted(gemini_counts.items(), key=lambda x: -x[1]):
    label, bg, fg = gemini_label_map.get(st, (st, GREY_L, GREY))
    desc_map = {
        "confirmed_present":   "Contract evidence clearly covers this GCC clause.",
        "partially_supported": "Evidence is partial or ambiguous for this clause.",
        "not_supported":       "Initial match is not backed by contract text.",
        "confirmed_missing":   "Clause is genuinely absent from the contract.",
        "needs_review":        "Evidence too weak; requires human legal review.",
    }
    g_rows.append([
        pill(label, bg, fg),
        Paragraph(str(cnt), ParagraphStyle("gc", fontSize=9, leading=11,
                                            fontName="Helvetica-Bold", textColor=fg,
                                            alignment=TA_RIGHT)),
        Paragraph(desc_map.get(st, ""), CELL),
    ])

g_tbl = Table(g_rows, colWidths=[W*0.30, W*0.12, W*0.58])
g_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
    ("TOPPADDING",    (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_L]),
    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E5E7EB")),
    ("LINEBELOW", (0, -1), (-1, -1), 1, BRAND_ACCENT),
]))
story.append(g_tbl)

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# PAGE 2+ — Full Clause Detail Table
# ════════════════════════════════════════════════════════════════════════════
story += section_title("Full Clause Analysis — All GCC Clauses")

intro = (
    "The following table lists every GCC clause checked against the contract, "
    "along with its risk category, detection method, page location, and the "
    "Gemini AI second-pass verdict."
)
story.append(Paragraph(intro, BODY))
story.append(Spacer(1, 8))

col_hdrs = ["Clause ID", "Title", "Risk", "Status", "Page", "Gemini Verdict", "Reason"]
detail_rows = [[Paragraph(h, HDR) for h in col_hdrs]]

detail_style = [
    ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
    ("TOPPADDING",    (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_L]),
    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
]

# Sort: HIGH risk missing first, then by status
def sort_key(c):
    risk_order_map = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    status_order   = {"truly_missing": 0, "needs_review": 1, "present_fuzzy": 2,
                      "present": 3}
    st = c.get("final_status") or c.get("status", "unknown")
    return (risk_order_map.get(c.get("risk_category", "LOW"), 3),
            status_order.get(st, 4))

for clause in sorted(clauses, key=sort_key):
    st    = clause.get("final_status") or clause.get("status", "unknown")
    g_st  = clause.get("gemini_status", "—")
    risk  = clause.get("risk_category", "")
    page  = str(clause.get("page_number", "—")) if clause.get("page_number") else "—"
    reason = clause.get("gemini_reason", "")
    if reason and len(reason) > 120:
        reason = reason[:117] + "…"

    sbg, sfg = status_color(st)
    gbg, gfg = status_color(g_st)
    rbg, rfg = risk_color(risk)

    detail_rows.append([
        Paragraph(f"<b>{clause.get('clause_id', '')}</b>", CELL_B),
        Paragraph(clause.get("clause_title", ""), CELL),
        pill(risk, rbg, rfg),
        pill(st.replace("_", " ").title(), sbg, sfg),
        Paragraph(page, ParagraphStyle("pg", fontSize=8, leading=10,
                                        fontName="Helvetica", alignment=TA_CENTER)),
        pill(g_st.replace("_", " ").title(), gbg, gfg),
        Paragraph(reason, SMALL),
    ])

detail_tbl = Table(
    detail_rows,
    colWidths=[W*0.11, W*0.19, W*0.07, W*0.13, W*0.05, W*0.14, W*0.31],
    repeatRows=1,
)
detail_tbl.setStyle(TableStyle(detail_style))
story.append(detail_tbl)

story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# PAGE — Missing Clauses Spotlight
# ════════════════════════════════════════════════════════════════════════════
story += section_title("⚠  Missing / At-Risk Clauses — Action Required")

missing = [c for c in clauses
           if (c.get("final_status") or c.get("status")) in {"truly_missing", "needs_review"}]
missing_sorted = sorted(missing, key=lambda c: {"HIGH":0,"MEDIUM":1,"LOW":2}.get(
    c.get("risk_category","LOW"),3))

if missing_sorted:
    m_rows = [[Paragraph(h, HDR) for h in
               ["Clause ID", "Title", "Risk", "Status", "Gemini Verdict", "AI Reason"]]]
    for c in missing_sorted:
        st   = c.get("final_status") or c.get("status", "")
        g_st = c.get("gemini_status", "—")
        risk = c.get("risk_category", "")
        sbg, sfg = status_color(st)
        gbg, gfg = status_color(g_st)
        rbg, rfg = risk_color(risk)
        reason = c.get("gemini_reason", "No AI reason available.")
        if len(reason) > 140:
            reason = reason[:137] + "…"
        m_rows.append([
            Paragraph(f"<b>{c.get('clause_id','')}</b>", CELL_B),
            Paragraph(c.get("clause_title", ""), CELL),
            pill(risk, rbg, rfg),
            pill(st.replace("_"," ").title(), sbg, sfg),
            pill(g_st.replace("_"," ").title(), gbg, gfg),
            Paragraph(reason, SMALL),
        ])
    m_tbl = Table(m_rows,
                  colWidths=[W*0.11, W*0.20, W*0.07, W*0.13, W*0.14, W*0.35],
                  repeatRows=1)
    m_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7F1D1D")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, RED_L]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
    ]))
    story.append(m_tbl)
else:
    story.append(Paragraph("✅  No missing or at-risk clauses found.", BODY))

story.append(Spacer(1, 20))

# ── Footer note ───────────────────────────────────────────────────────────────
story.append(HR())
story.append(Paragraph(
    "This report was generated automatically by <b>Clauset AI</b> using Google Gemini. "
    "All findings should be reviewed by a qualified legal professional before taking contractual action. "
    f"Generated on {now}.",
    ParagraphStyle("footer", fontSize=7.5, leading=11, textColor=GREY,
                   fontName="Helvetica", alignment=TA_CENTER)
))

# ── Build ─────────────────────────────────────────────────────────────────────
doc.build(story)
print(f"\n✅  Report saved to: {OUTPUT_PATH}")
