"""
core/report_generator.py

PDF report builder for the Railway GCC Contract Risk Analyzer.
Uses ReportLab to generate a multi-page, colour-coded PDF report
containing the full clause-by-clause risk analysis results.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.colors import HexColor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
COLOUR_HIGH = HexColor("#C0392B")       # Red
COLOUR_MEDIUM = HexColor("#E67E22")     # Orange
COLOUR_LOW = HexColor("#F1C40F")        # Yellow
COLOUR_COMPLIANT = HexColor("#27AE60")  # Green
COLOUR_BG_DARK = HexColor("#1A2332")    # Cover page background
COLOUR_ACCENT = HexColor("#2980B9")     # Section headings
COLOUR_LIGHT_GREY = HexColor("#F5F6FA")
COLOUR_TEXT = HexColor("#2C3E50")
COLOUR_WHITE = colors.white

RISK_COLOURS: Dict[str, HexColor] = {
    "HIGH": COLOUR_HIGH,
    "MEDIUM": COLOUR_MEDIUM,
    "LOW": COLOUR_LOW,
    "COMPLIANT": COLOUR_COMPLIANT,
}

RISK_TEXT_COLOURS: Dict[str, HexColor] = {
    "HIGH": COLOUR_WHITE,
    "MEDIUM": COLOUR_WHITE,
    "LOW": COLOUR_TEXT,
    "COMPLIANT": COLOUR_WHITE,
}


def _risk_colour(risk_level: str) -> HexColor:
    return RISK_COLOURS.get(risk_level.upper(), COLOUR_LOW)


def _risk_text_colour(risk_level: str) -> HexColor:
    return RISK_TEXT_COLOURS.get(risk_level.upper(), COLOUR_TEXT)


class ReportBuilder:
    """
    Builds a multi-page, colour-coded PDF risk report using ReportLab.

    Pages:
      1. Cover page — title, filename, date, overall risk score
      2. Executive summary
      3+. One section per clause analysis
      Last. Legal disclaimer
    """

    def __init__(self) -> None:
        """
        Initialise the ReportBuilder with ReportLab styles and custom paragraph styles.
        """
        self.base_styles = getSampleStyleSheet()
        self._build_custom_styles()

    # ------------------------------------------------------------------
    # Style setup
    # ------------------------------------------------------------------

    def _build_custom_styles(self) -> None:
        """Define all custom paragraph styles used throughout the report."""
        self.style_cover_title = ParagraphStyle(
            name="CoverTitle",
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=36,
            textColor=COLOUR_WHITE,
            alignment=TA_CENTER,
            spaceAfter=10 * mm,
        )
        self.style_cover_subtitle = ParagraphStyle(
            name="CoverSubtitle",
            fontName="Helvetica",
            fontSize=14,
            leading=18,
            textColor=HexColor("#BDC3C7"),
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        )
        self.style_cover_meta = ParagraphStyle(
            name="CoverMeta",
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=HexColor("#ECF0F1"),
            alignment=TA_CENTER,
        )
        self.style_section_heading = ParagraphStyle(
            name="SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=22,
            textColor=COLOUR_ACCENT,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
        )
        self.style_clause_heading = ParagraphStyle(
            name="ClauseHeading",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=18,
            textColor=COLOUR_TEXT,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        )
        self.style_body = ParagraphStyle(
            name="BodyText",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=COLOUR_TEXT,
            alignment=TA_JUSTIFY,
            spaceAfter=3 * mm,
        )
        self.style_bullet = ParagraphStyle(
            name="BulletText",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=COLOUR_TEXT,
            leftIndent=12 * mm,
            spaceAfter=2 * mm,
            bulletIndent=6 * mm,
        )
        self.style_numbered = ParagraphStyle(
            name="NumberedText",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=COLOUR_TEXT,
            leftIndent=12 * mm,
            spaceAfter=2 * mm,
        )
        self.style_label = ParagraphStyle(
            name="LabelText",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=COLOUR_TEXT,
            spaceAfter=1 * mm,
        )
        self.style_disclaimer = ParagraphStyle(
            name="Disclaimer",
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=14,
            textColor=HexColor("#7F8C8D"),
            alignment=TA_JUSTIFY,
            spaceAfter=3 * mm,
        )
        self.style_exec_heading = ParagraphStyle(
            name="ExecHeading",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=24,
            textColor=COLOUR_ACCENT,
            spaceBefore=8 * mm,
            spaceAfter=4 * mm,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        analyses: List[Dict[str, Any]],
        executive_summary: str,
        pdf_filename: str,
        output_path: str,
    ) -> str:
        """
        Build the full risk report PDF and save it to output_path.

        Args:
            analyses:          List of clause analysis dicts from GroqAnalyzer.
            executive_summary: Plain-text executive summary from summarize_full_report().
            pdf_filename:      Original uploaded PDF filename (displayed on cover).
            output_path:       Absolute path where the PDF report will be written.

        Returns:
            The output_path string (for easy chaining in app.py).
        """
        logger.info("Building PDF report at: %s", output_path)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title="GCC Compliance Risk Report",
            author="Railway GCC Contract Risk Analyzer",
        )

        story = []

        # Page 1: Cover
        story.extend(self._build_cover_page(analyses, pdf_filename))
        story.append(PageBreak())

        # Page 2: Executive Summary
        story.extend(self._build_executive_summary_page(executive_summary))
        story.append(PageBreak())

        # Pages 3+: Clause analyses
        for idx, analysis in enumerate(analyses, start=1):
            story.extend(self._build_clause_section(analysis, idx))

        # Final page: Disclaimer
        story.append(PageBreak())
        story.extend(self._build_disclaimer_page())

        try:
            doc.build(story)
            logger.info("PDF report built successfully: %s", output_path)
        except Exception as exc:
            logger.error("ReportLab PDF build failed: %s", exc)
            raise

        return output_path

    # ------------------------------------------------------------------
    # Page builders
    # ------------------------------------------------------------------

    def _build_cover_page(
        self, analyses: List[Dict[str, Any]], pdf_filename: str
    ) -> List[Any]:
        """
        Build the cover page elements.

        Args:
            analyses:     All clause analysis results.
            pdf_filename: Name of the uploaded contract file.

        Returns:
            List of ReportLab flowables for the cover page.
        """
        elements = []

        # Risk counts
        risk_counts: Dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "COMPLIANT": 0}
        for a in analyses:
            lvl = a.get("risk_level", "LOW").upper()
            risk_counts[lvl] = risk_counts.get(lvl, 0) + 1

        total = len(analyses)
        high_count = risk_counts["HIGH"]

        # Determine overall risk
        if high_count > 0:
            overall_risk = "HIGH"
        elif risk_counts["MEDIUM"] > 0:
            overall_risk = "MEDIUM"
        elif risk_counts["LOW"] > 0:
            overall_risk = "LOW"
        else:
            overall_risk = "COMPLIANT"

        overall_colour = _risk_colour(overall_risk)

        # Coloured banner header block via Table
        page_w, _ = A4
        inner_w = page_w - 40 * mm  # accounting for margins

        banner_data = [[
            Paragraph(
                "RAILWAY GCC CONTRACT<br/>RISK ANALYSIS REPORT",
                self.style_cover_title,
            )
        ]]
        banner = Table(banner_data, colWidths=[inner_w])
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOUR_BG_DARK),
            ("TOPPADDING", (0, 0), (-1, -1), 20 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 20 * mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 10 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10 * mm),
            ("ROUNDEDCORNERS", [3 * mm]),
        ]))
        elements.append(banner)
        elements.append(Spacer(1, 10 * mm))

        # File info table
        now_str = datetime.now().strftime("%d %B %Y, %H:%M")
        info_data = [
            ["Contract File:", pdf_filename or "Unknown"],
            ["Date Generated:", now_str],
            ["Total Clauses Analysed:", str(total)],
            ["Overall Risk Rating:", overall_risk],
        ]
        info_table = Table(info_data, colWidths=[60 * mm, inner_w - 60 * mm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("TEXTCOLOR", (0, 0), (-1, -1), COLOUR_TEXT),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOUR_LIGHT_GREY, COLOUR_WHITE]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#BDC3C7")),
            ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
            # Colour the overall risk cell
            ("TEXTCOLOR", (1, 3), (1, 3), overall_colour),
            ("FONTNAME", (1, 3), (1, 3), "Helvetica-Bold"),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8 * mm))

        # Risk breakdown table
        elements.append(Paragraph("Risk Breakdown Summary", self.style_section_heading))

        breakdown_header = [["Risk Level", "Count", "Status"]]
        breakdown_rows = [
            ["HIGH", str(risk_counts["HIGH"]), "Critical — Immediate Action Required"],
            ["MEDIUM", str(risk_counts["MEDIUM"]), "Elevated — Review Recommended"],
            ["LOW", str(risk_counts["LOW"]), "Caution — Monitor Closely"],
            ["COMPLIANT", str(risk_counts["COMPLIANT"]), "No Deviation Found"],
        ]
        breakdown_data = breakdown_header + breakdown_rows
        breakdown_table = Table(
            breakdown_data,
            colWidths=[40 * mm, 30 * mm, inner_w - 70 * mm],
        )
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOUR_BG_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOUR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#BDC3C7")),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]
        # Colour the risk-level cells
        colour_map = {1: COLOUR_HIGH, 2: COLOUR_MEDIUM, 3: COLOUR_LOW, 4: COLOUR_COMPLIANT}
        text_map = {
            1: COLOUR_WHITE, 2: COLOUR_WHITE,
            3: COLOUR_TEXT, 4: COLOUR_WHITE,
        }
        for row_idx, row_colour in colour_map.items():
            style_cmds.append(
                ("BACKGROUND", (0, row_idx), (0, row_idx), row_colour)
            )
            style_cmds.append(
                ("TEXTCOLOR", (0, row_idx), (0, row_idx), text_map[row_idx])
            )
            style_cmds.append(
                ("FONTNAME", (0, row_idx), (0, row_idx), "Helvetica-Bold")
            )

        breakdown_table.setStyle(TableStyle(style_cmds))
        elements.append(breakdown_table)

        return elements

    def _build_executive_summary_page(self, executive_summary: str) -> List[Any]:
        """
        Build the executive summary page elements.

        Args:
            executive_summary: Plain-text summary from GroqAnalyzer.

        Returns:
            List of ReportLab flowables.
        """
        elements: List[Any] = []
        elements.append(Paragraph("Executive Summary", self.style_exec_heading))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOUR_ACCENT))
        elements.append(Spacer(1, 5 * mm))

        for para_text in executive_summary.split("\n\n"):
            text = para_text.strip()
            if text:
                elements.append(Paragraph(text, self.style_body))
                elements.append(Spacer(1, 2 * mm))

        return elements

    def _build_clause_section(
        self, analysis: Dict[str, Any], clause_index: int
    ) -> List[Any]:
        """
        Build the analysis section for a single clause.

        Args:
            analysis:     A single clause analysis dict from GroqAnalyzer.
            clause_index: 1-based index of this clause in the report.

        Returns:
            List of ReportLab flowables for this clause section.
        """
        elements: List[Any] = []

        risk_level = str(analysis.get("risk_level", "LOW")).upper()
        summary = str(analysis.get("summary", "No summary available."))
        deviations: List[str] = analysis.get("deviations", [])
        recommendations: List[str] = analysis.get("recommendations", [])
        clause_ids: List[str] = analysis.get("relevant_clause_ids", [])

        risk_colour = _risk_colour(risk_level)
        risk_text_colour = _risk_text_colour(risk_level)

        # Clause header row: "Clause N" + risk badge side by side
        page_w, _ = A4
        inner_w = page_w - 40 * mm

        badge_data = [[
            Paragraph(f"Clause {clause_index}", self.style_clause_heading),
            Paragraph(
                f"<b> {risk_level} RISK </b>",
                ParagraphStyle(
                    name=f"Badge_{clause_index}",
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    textColor=risk_text_colour,
                    alignment=TA_CENTER,
                ),
            ),
        ]]
        badge_table = Table(badge_data, colWidths=[inner_w - 35 * mm, 35 * mm])
        badge_table.setStyle(TableStyle([
            ("BACKGROUND", (1, 0), (1, 0), risk_colour),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("ROUNDEDCORNERS", [2 * mm]),
        ]))

        clause_block = [
            badge_table,
            Spacer(1, 2 * mm),
            HRFlowable(width="100%", thickness=0.5, color=HexColor("#BDC3C7")),
            Spacer(1, 2 * mm),
        ]

        # Summary
        clause_block.append(Paragraph("<b>Summary</b>", self.style_label))
        clause_block.append(Paragraph(summary, self.style_body))
        clause_block.append(Spacer(1, 2 * mm))

        # Deviations
        if deviations:
            clause_block.append(Paragraph("<b>Deviations Found</b>", self.style_label))
            for dev in deviations:
                clause_block.append(
                    Paragraph(f"• {dev}", self.style_bullet)
                )
            clause_block.append(Spacer(1, 2 * mm))

        # Recommendations
        if recommendations:
            clause_block.append(Paragraph("<b>Recommendations</b>", self.style_label))
            for i, rec in enumerate(recommendations, start=1):
                clause_block.append(
                    Paragraph(f"{i}. {rec}", self.style_numbered)
                )
            clause_block.append(Spacer(1, 2 * mm))

        # GCC clause IDs matched
        if clause_ids:
            ids_str = "  |  ".join(clause_ids)
            clause_block.append(
                Paragraph(f"<b>Matched GCC Clauses:</b>  {ids_str}", self.style_label)
            )
            clause_block.append(Spacer(1, 2 * mm))

        # Wrap entire block in KeepTogether to avoid mid-clause page breaks
        elements.append(KeepTogether(clause_block))
        elements.append(Spacer(1, 5 * mm))

        return elements

    def _build_disclaimer_page(self) -> List[Any]:
        """
        Build the legal disclaimer page.

        Returns:
            List of ReportLab flowables for the disclaimer page.
        """
        elements: List[Any] = []

        elements.append(Paragraph("Important Legal Disclaimer", self.style_section_heading))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOUR_ACCENT))
        elements.append(Spacer(1, 5 * mm))

        disclaimer_paragraphs = [
            (
                "This report has been generated automatically by the Railway GCC Contract Risk "
                "Analyzer, an AI-powered tool that uses large language models (LLMs) and semantic "
                "search to identify potential deviations from the Indian Railways General Conditions "
                "of Contract (GCC). The analysis is intended to assist contract review teams and "
                "project managers in identifying areas of concern and should not be relied upon as "
                "a definitive legal opinion."
            ),
            (
                "The AI system may make errors, omissions, or misinterpretations. Contract law and "
                "Railway GCC provisions are complex legal instruments that require professional "
                "legal expertise to interpret accurately in the context of specific transactions and "
                "circumstances. This report does not constitute legal advice and should not be used "
                "as a substitute for advice from a qualified lawyer or legal counsel with expertise "
                "in Indian contract law and Railways regulations."
            ),
            (
                "All findings, risk ratings, deviations, and recommendations contained in this "
                "report must be reviewed and verified by a qualified legal expert before any "
                "contractual decisions are made. The developers of this tool expressly disclaim "
                "all liability arising from reliance on the content of this report."
            ),
            (
                "The GCC rules database embedded in this tool is based on publicly available "
                "Indian Railways General Conditions of Contract. Users should ensure they reference "
                "the most current version of the GCC as issued by the Ministry of Railways, "
                "Government of India, as the rules may be amended from time to time."
            ),
        ]

        for para in disclaimer_paragraphs:
            elements.append(Paragraph(para, self.style_disclaimer))
            elements.append(Spacer(1, 3 * mm))

        # Footer note
        elements.append(Spacer(1, 10 * mm))
        generated_at = datetime.now().strftime("%d %B %Y at %H:%M")
        elements.append(
            Paragraph(
                f"Report generated on {generated_at} by Railway GCC Contract Risk Analyzer v1.0",
                self.style_disclaimer,
            )
        )

        return elements
