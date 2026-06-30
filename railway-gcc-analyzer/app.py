"""
app.py

Main entry point for the Railway GCC Contract Risk Analyzer.
Initialises all subsystems on startup and exposes a Gradio web interface
where users upload a PDF contract, run the full analysis pipeline,
and download a colour-coded PDF risk report.

Pipeline:
  1. PDF extraction (PyMuPDF + OCR fallback)
  2. Two-stage text chunking (header-based → word-count fallback)
  3. Semantic GCC rule retrieval via ChromaDB
  4. Batched LLM analysis via Groq (≤ 3 clauses per API call)
  5. Executive summary generation
  6. PDF report generation via ReportLab
"""

import os
import time
import math
import logging
import tempfile
from datetime import datetime
from typing import Tuple, Optional

import gradio as gr
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables before importing core modules
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import core modules and GCC rules data
# ---------------------------------------------------------------------------
from core.ocr_engine import PDFExtractor
from core.vector_store import GCCVectorStore
from core.groq_client import GroqAnalyzer
from core.report_generator import ReportBuilder
from data.gcc_rules import GCC_RULES

# ---------------------------------------------------------------------------
# SECTION 1: INITIALISATION
# ---------------------------------------------------------------------------

logger.info("Initialising GCC Vector Store...")
vector_store = GCCVectorStore(persist_dir="./chroma_db")

logger.info("Populating GCC Vector Store with rules (skipped if already populated)...")
vector_store.populate(GCC_RULES)

logger.info("Initialising Groq Analyzer...")
groq_analyzer = GroqAnalyzer()

logger.info("Initialising Report Builder...")
report_builder = ReportBuilder()

logger.info("All subsystems initialised. Ready to accept requests.")

# ---------------------------------------------------------------------------
# SECTION 2: CORE PIPELINE FUNCTION
# ---------------------------------------------------------------------------

PDF_MAGIC_BYTES = b"%PDF"


def _is_valid_pdf(file_path: str) -> bool:
    """
    Check whether the file at file_path is a valid PDF by inspecting its magic bytes.

    Args:
        file_path: Absolute path to the file to check.

    Returns:
        True if the file starts with the PDF magic bytes (%PDF), False otherwise.
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
        return header == PDF_MAGIC_BYTES
    except OSError as exc:
        logger.error("Could not read file for magic byte check: %s", exc)
        return False


def analyze_contract(
    pdf_file,
    progress: gr.Progress = gr.Progress(),
) -> Tuple[str, str, Optional[str]]:
    """
    Run the full contract analysis pipeline on an uploaded PDF file.

    In Gradio 6, an uploaded file is passed as a dict with a 'path' key
    (e.g. {'path': '/tmp/gradio/...', 'orig_name': '...', ...}).

    Args:
        pdf_file: Gradio file dict for the uploaded PDF, or None.
        progress: Gradio progress tracker for the UI progress bar.

    Returns:
        A 3-tuple of:
          - status_message  : str  — final status or error message shown in the textbox
          - stats_markdown  : str  — Markdown-formatted analysis stats table
          - pdf_output_path : str | None — path to the generated PDF report (or None on error)
    """

    # -----------------------------------------------------------------------
    # Input validation
    # -----------------------------------------------------------------------
    if pdf_file is None:
        return (
            "❌ No file uploaded. Please upload a PDF contract and try again.",
            "",
            None,
        )

    # Gradio 6 passes uploaded files as dicts: {'path': ..., 'orig_name': ...}
    # Older Gradio passed objects with a .name attribute.
    if isinstance(pdf_file, dict):
        file_path: str = pdf_file.get("path", "")
        original_filename: str = pdf_file.get("orig_name") or os.path.basename(file_path)
    else:
        # Fallback for any other Gradio version
        file_path = getattr(pdf_file, "name", str(pdf_file))
        original_filename = os.path.basename(file_path)

    if not file_path or not os.path.isfile(file_path):
        return (
            "❌ Could not locate the uploaded file on disk. Please try uploading again.",
            "",
            None,
        )

    if not _is_valid_pdf(file_path):
        return (
            "❌ The uploaded file does not appear to be a valid PDF "
            "(magic bytes check failed). Please upload a genuine PDF file.",
            "",
            None,
        )

    try:
        # -------------------------------------------------------------------
        # Step 1 — PDF text extraction (10%)
        # -------------------------------------------------------------------
        progress(0.10, desc="Step 1/7 — Extracting text from PDF...")

        extractor = PDFExtractor()
        extraction_result = extractor.extract(file_path)

        full_text: str = extraction_result["full_text"]
        page_count: int = extraction_result["page_count"]
        method_used: str = extraction_result["method_used"]

        if not full_text.strip():
            return (
                "❌ Could not extract any text from the uploaded PDF. "
                "The file may be blank, encrypted, or corrupted.",
                "",
                None,
            )

        status_step1 = (
            f"✅ Step 1 complete — Extracted {len(full_text):,} characters "
            f"from {page_count} pages using {method_used.upper()} method."
        )
        logger.info(status_step1)

        # -------------------------------------------------------------------
        # Step 2 — Text chunking (30%)
        # -------------------------------------------------------------------
        progress(0.30, desc="Step 2/7 — Chunking document into clauses...")

        chunks = extractor.chunk_text(full_text)

        # Detect which chunking strategy was used
        # Header-based chunks tend to be much longer than word-count chunks
        if len(chunks) > 0 and len(chunks) < 60:
            avg_words = sum(len(c.split()) for c in chunks) / len(chunks)
            chunking_method = (
                "header-based" if avg_words > 200 else "word-count fallback"
            )
        else:
            chunking_method = "word-count fallback"

        status_step2 = (
            f"✅ Step 2 complete — {len(chunks)} chunks produced "
            f"using {chunking_method} chunking."
        )
        logger.info(status_step2)

        # -------------------------------------------------------------------
        # Step 3 — GCC rules retrieval (50%)
        # -------------------------------------------------------------------
        progress(0.50, desc="Step 3/7 — Querying GCC rules database...")

        seen_rule_ids: set = set()
        relevant_chunks = []  # list of (chunk_text, matched_rules)

        for chunk in chunks:
            matched_rules = vector_store.query(chunk, n_results=3)
            if not matched_rules:
                continue  # Skip chunks with no matching GCC rule

            # Deduplicate matched rules globally
            unique_rules = []
            for rule in matched_rules:
                rule_id = rule.get("clause_id", "")
                if rule_id not in seen_rule_ids:
                    seen_rule_ids.add(rule_id)
                    unique_rules.append(rule)

            # Include the chunk even if all rules were already seen — we still
            # want to analyse it, but pass only truly matched rules for this chunk
            if matched_rules:
                relevant_chunks.append({
                    "chunk_text": chunk,
                    "matched_rules": matched_rules,
                })

        total_relevant = len(relevant_chunks)
        total_rules_matched = len(seen_rule_ids)

        status_step3 = (
            f"✅ Step 3 complete — {total_relevant} relevant chunks found "
            f"matching {total_rules_matched} unique GCC rules."
        )
        logger.info(status_step3)

        if total_relevant == 0:
            return (
                "⚠️ No clauses in the uploaded contract matched any GCC rules. "
                "The document may not be a Railway GCC-type contract, "
                "or the text extraction may have failed. "
                "Please check the document and try again.",
                "",
                None,
            )

        # -------------------------------------------------------------------
        # Step 4 — Batched Groq LLM analysis (70%)
        # -------------------------------------------------------------------
        progress(0.55, desc="Step 4/7 — Analyzing clauses with Groq AI (batched)...")

        # Cap relevant chunks to avoid excessively long analysis on free tier
        MAX_CHUNKS = 30
        if total_relevant > MAX_CHUNKS:
            logger.warning(
                "⚠️ Large contract detected (%d relevant clauses). "
                "Capping analysis to the top %d most relevant clauses "
                "to stay within Groq free-tier rate limits.",
                total_relevant,
                MAX_CHUNKS,
            )
            relevant_chunks = relevant_chunks[:MAX_CHUNKS]
            total_relevant = MAX_CHUNKS

        # Large-contract time estimate
        total_batches = math.ceil(total_relevant / 3)
        estimated_minutes = math.ceil(total_batches * 0.35)  # ~20s per batch
        logger.info(
            "Processing %d clauses in %d batches. Estimated time: ~%d minutes.",
            total_relevant,
            total_batches,
            estimated_minutes,
        )

        # Build batches of at most 3 chunks
        batches = []
        for i in range(0, total_relevant, 3):
            batches.append(relevant_chunks[i : i + 3])

        all_analyses = []

        for batch_idx, batch in enumerate(batches):
            batch_progress_start = 0.55
            batch_progress_end = 0.70
            batch_fraction = (batch_idx + 1) / len(batches)
            current_progress = batch_progress_start + (
                batch_fraction * (batch_progress_end - batch_progress_start)
            )
            progress(
                current_progress,
                desc=(
                    f"Step 4/7 — Analysing batch {batch_idx + 1}/{len(batches)} "
                    f"({len(batch)} clauses)..."
                ),
            )

            # Build the batch input list with chunk labels
            batch_input = []
            for chunk_idx, item in enumerate(batch):
                global_chunk_num = batch_idx * 3 + chunk_idx + 1
                # Try to extract a header label from the chunk text
                chunk_label = _extract_chunk_label(
                    item["chunk_text"], global_chunk_num
                )
                batch_input.append({
                    "chunk_text": item["chunk_text"],
                    "chunk_label": chunk_label,
                    "matched_rules": item["matched_rules"],
                })

            batch_results = groq_analyzer.analyze_clauses_batch(batch_input)
            all_analyses.extend(batch_results)

            # Rate-limit pause between batches — Groq free tier needs ~15s
            # between batch calls to stay within TPM limits
            if batch_idx < len(batches) - 1:
                time.sleep(15)

        time_saved_seconds = (total_relevant - len(batches)) * 18
        status_step4 = (
            f"✅ Step 4 complete — Analysed {len(all_analyses)} clauses "
            f"in {len(batches)} batches. "
            f"Estimated time saved vs unbatched: {time_saved_seconds}s."
        )
        logger.info(status_step4)

        # -------------------------------------------------------------------
        # Step 5 — Executive summary (85%)
        # -------------------------------------------------------------------
        progress(0.85, desc="Step 5/7 — Generating executive summary...")

        executive_summary = groq_analyzer.summarize_full_report(all_analyses)

        status_step5 = "✅ Step 5 complete — Executive summary generated."
        logger.info(status_step5)

        # -------------------------------------------------------------------
        # Step 6 — Build PDF report (95%)
        # -------------------------------------------------------------------
        progress(0.95, desc="Step 6/7 — Building PDF report...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"gcc_report_{timestamp}.pdf"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)

        report_builder.build(
            analyses=all_analyses,
            executive_summary=executive_summary,
            pdf_filename=original_filename,
            output_path=output_path,
        )

        status_step6 = f"✅ Step 6 complete — PDF report saved to {output_path}"
        logger.info(status_step6)

        # -------------------------------------------------------------------
        # Step 7 — Done (100%)
        # -------------------------------------------------------------------
        progress(1.0, desc="Step 7/7 — Done!")

        # Build risk breakdown counts
        risk_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "COMPLIANT": 0}
        for a in all_analyses:
            lvl = str(a.get("risk_level", "LOW")).upper()
            risk_counts[lvl] = risk_counts.get(lvl, 0) + 1

        final_status = (
            f"✅ Analysis complete!\n\n"
            f"• Pages processed       : {page_count}\n"
            f"• Extraction method     : {method_used.upper()}\n"
            f"• Chunking method       : {chunking_method}\n"
            f"• Clauses analysed      : {len(all_analyses)}\n"
            f"• Batches sent to Groq  : {len(batches)}\n"
            f"• Time saved (batching) : ~{time_saved_seconds}s\n"
            f"• GCC rules matched     : {total_rules_matched}\n\n"
            f"📄 PDF report is ready for download below."
        )

        stats_markdown = _build_stats_markdown(
            total_clauses=len(all_analyses),
            risk_counts=risk_counts,
            method_used=method_used,
            chunking_method=chunking_method,
            rules_matched=total_rules_matched,
            page_count=page_count,
        )

        return final_status, stats_markdown, output_path

    except Exception as exc:
        logger.exception("Unhandled error during contract analysis: %s", exc)
        error_msg = (
            f"❌ An unexpected error occurred during analysis:\n{type(exc).__name__}: {exc}\n\n"
            "Please check the logs for details. If the problem persists, "
            "try uploading a different PDF or contact the administrator."
        )
        return error_msg, "", None


def _extract_chunk_label(chunk_text: str, fallback_num: int) -> str:
    """
    Try to extract a human-readable label from the first line of a chunk.

    Looks for patterns like "Clause 47", "47.1", "Section 3" at the start.
    Falls back to "Chunk N" if no recognisable header is found.

    Args:
        chunk_text:   The text of the chunk.
        fallback_num: Chunk sequence number used if no header is detected.

    Returns:
        A short label string, e.g. "Clause 47" or "Chunk 3".
    """
    import re
    first_line = chunk_text.strip().split("\n")[0][:100]
    header_match = re.search(
        r"((?:Clause|CLAUSE|Section|SECTION|Article|ARTICLE)\s+\d+(?:\.\d+)*"
        r"|\d+\.\d+(?:\.\d+)*|\d+\.)",
        first_line,
    )
    if header_match:
        return header_match.group(0).strip()
    return f"Chunk {fallback_num}"


def _build_stats_markdown(
    total_clauses: int,
    risk_counts: dict,
    method_used: str,
    chunking_method: str,
    rules_matched: int,
    page_count: int,
) -> str:
    """
    Build the Markdown string displayed in the stats panel after analysis.

    Args:
        total_clauses:   Total number of clauses analysed.
        risk_counts:     Dict mapping risk level strings to counts.
        method_used:     PDF extraction method ("digital", "ocr", or "mixed").
        chunking_method: Chunking strategy used ("header-based" or "word-count fallback").
        rules_matched:   Number of unique GCC rules matched.
        page_count:      Number of pages in the uploaded PDF.

    Returns:
        A Markdown-formatted string for gr.Markdown display.
    """
    high = risk_counts.get("HIGH", 0)
    medium = risk_counts.get("MEDIUM", 0)
    low = risk_counts.get("LOW", 0)
    compliant = risk_counts.get("COMPLIANT", 0)

    md = f"""
## 📊 Analysis Results

| Metric | Value |
|--------|-------|
| **Pages Processed** | {page_count} |
| **Total Clauses Analysed** | {total_clauses} |
| **GCC Rules Matched** | {rules_matched} |
| **Extraction Method** | {method_used.upper()} |
| **Chunking Method** | {chunking_method.title()} |

---

### ⚠️ Risk Breakdown

| Risk Level | Count | Action Required |
|------------|-------|-----------------|
| 🔴 **HIGH** | {high} | Immediate review & renegotiation |
| 🟠 **MEDIUM** | {medium} | Legal review recommended |
| 🟡 **LOW** | {low} | Monitor and note |
| 🟢 **COMPLIANT** | {compliant} | No action needed |

---

> 📄 **Download the full PDF report below for clause-by-clause details, deviations, and recommendations.**
"""
    return md.strip()


# ---------------------------------------------------------------------------
# SECTION 3: GRADIO UI
# ---------------------------------------------------------------------------

CSS = """
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
#header-title {
    text-align: center;
    margin-bottom: 0.5rem;
}
#header-subtitle {
    text-align: center;
    color: #666;
    margin-bottom: 1.5rem;
    font-size: 0.95rem;
}
#analyze-btn {
    width: 100%;
    font-size: 1rem;
    font-weight: 600;
}
#status-box textarea {
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
}
#footer-text {
    text-align: center;
    font-size: 0.78rem;
    color: #999;
    margin-top: 1.5rem;
    padding-top: 0.75rem;
    border-top: 1px solid #e0e0e0;
}
.risk-table {
    width: 100%;
}
"""

with gr.Blocks(
    title="Railway GCC Contract Risk Analyzer",
) as demo:

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    gr.HTML(
        """
        <div id="header-title">
            <h1 style="font-size:1.8rem; font-weight:700; color:#1a2332;">
                🚂 Railway GCC Contract Risk Analyzer
            </h1>
        </div>
        <div id="header-subtitle">
            Upload a Railway contract PDF. The system will extract clauses, compare them
            against the official Indian Railways GCC rule database using AI, and generate
            a detailed, colour-coded risk report you can download.
        </div>
        """
    )

    # -----------------------------------------------------------------------
    # Row 1: File Upload
    # -----------------------------------------------------------------------
    with gr.Row():
        pdf_upload = gr.File(
            label="📂 Upload Contract PDF (max 50 MB)",
            file_types=[".pdf"],
            file_count="single",
            elem_id="pdf-upload",
        )

    # -----------------------------------------------------------------------
    # Row 2: Analyse button
    # -----------------------------------------------------------------------
    with gr.Row():
        analyze_btn = gr.Button(
            "🔍 Analyse Contract",
            variant="primary",
            elem_id="analyze-btn",
            size="lg",
        )

    # -----------------------------------------------------------------------
    # Row 3: Status box
    # -----------------------------------------------------------------------
    with gr.Row():
        status_box = gr.Textbox(
            label="📋 Analysis Status",
            lines=10,
            max_lines=15,
            interactive=False,
            placeholder="Upload a PDF and click 'Analyse Contract' to begin...",
            elem_id="status-box",
        )

    # -----------------------------------------------------------------------
    # Row 4: Stats panel
    # -----------------------------------------------------------------------
    with gr.Row():
        stats_panel = gr.Markdown(
            value="",
            label="Analysis Statistics",
            elem_id="stats-panel",
        )

    # -----------------------------------------------------------------------
    # Row 5: Download button (hidden until analysis completes)
    # -----------------------------------------------------------------------
    with gr.Row():
        pdf_download = gr.File(
            label="⬇️ Download Risk Report (PDF)",
            visible=False,
            interactive=False,
            elem_id="pdf-download",
        )

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------
    gr.HTML(
        """
        <div id="footer-text">
            ⚠️ This tool provides AI-generated analysis for informational purposes only.
            All outputs must be reviewed by a qualified legal expert before acting on them.
            Railway GCC Contract Risk Analyzer v1.0 — built for Hugging Face Spaces.
        </div>
        """
    )

    # -----------------------------------------------------------------------
    # Event wiring
    # -----------------------------------------------------------------------

    def _run_analysis_and_show_download(pdf_file, progress=gr.Progress()):
        """
        Wrapper that runs the pipeline and toggles the download component visibility.

        Args:
            pdf_file: Gradio file dict from the upload component (Gradio 6 format).
            progress: Gradio progress object.

        Returns:
            Tuple of (status_text, stats_markdown, file_component_update).
        """
        status, stats_md, pdf_path = analyze_contract(pdf_file, progress)

        if pdf_path is not None and os.path.isfile(pdf_path):
            # Gradio 6: use gr.update() to update component properties
            download_update = gr.update(value=pdf_path, visible=True)
        else:
            download_update = gr.update(visible=False)

        return status, stats_md, download_update

    analyze_btn.click(
        fn=_run_analysis_and_show_download,
        inputs=[pdf_upload],
        outputs=[status_box, stats_panel, pdf_download],
        api_name="analyze",
    )

# ---------------------------------------------------------------------------
# SECTION 4: LAUNCH
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo.launch(
        auth=[("admin", os.getenv("APP_PASSWORD", "gcc2024"))],
        share=False,
        server_name="127.0.0.1",
        server_port=7860,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="gray",
        ),
        css=CSS,
    )
