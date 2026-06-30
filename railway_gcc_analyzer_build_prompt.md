# Railway GCC Contract Risk Analyzer — Master Build Prompt

> Paste everything below this line into Claude, Cursor, or any AI coding tool.

---

```
You are an expert Python developer. Build me a complete, production-ready,
fully deployable web application from scratch. Do not skip any file.
Do not leave placeholder comments. Write every function completely.

=======================================================================
PROJECT: Railway GCC Contract Risk Analyzer
=======================================================================

OBJECTIVE:
Build a web app where a user uploads a PDF contract (up to 100 pages),
the system extracts the text, compares specific clauses against a
pre-loaded Railway General Conditions of Contract (GCC) rule database,
and uses an LLM to generate a detailed risk analysis report that the
user can download.

=======================================================================
TECH STACK (use exactly these, no substitutions)
=======================================================================

- UI Framework     : Gradio (latest version)
- Hosting Target   : Hugging Face Spaces (CPU Basic, free tier)
- PDF Text Extract : PyMuPDF (fitz) — primary method
- OCR Engine       : Pytesseract + Pillow — fallback for scanned PDFs
- Vector Database  : ChromaDB (local, persistent, runs inside HF Space)
- Embedding Model  : sentence-transformers (all-MiniLM-L6-v2)
- LLM API          : Groq API (model: llama3-70b-8192)
- PDF Report Gen   : ReportLab
- Auth             : Gradio built-in auth parameter
- Env Variables    : python-dotenv

=======================================================================
PROJECT FILE STRUCTURE (create every single file listed below)
=======================================================================

railway-gcc-analyzer/
│
├── app.py                  ← Main Gradio app (entry point)
├── requirements.txt        ← All dependencies, pinned versions
├── .env.example            ← Template showing required env vars
├── README.md               ← Setup and deployment instructions
│
├── core/
│   ├── __init__.py
│   ├── ocr_engine.py       ← PDF extraction logic
│   ├── vector_store.py     ← ChromaDB setup and retrieval
│   ├── groq_client.py      ← Groq API call logic
│   └── report_generator.py ← ReportLab PDF report builder
│
└── data/
    └── gcc_rules.py        ← The GCC rules dataset (hardcoded)

=======================================================================
DETAILED INSTRUCTIONS FOR EACH FILE
=======================================================================

--- FILE: data/gcc_rules.py ---

Create a Python list of dictionaries called GCC_RULES.
Each dictionary must have these exact keys:
  - "clause_id"     : string, e.g. "GCC-47.1"
  - "clause_title"  : string, e.g. "Termination by Employer"
  - "clause_text"   : string, a realistic and detailed description
                       of what this Railway GCC clause mandates,
                       written as if it came from a real legal document
  - "risk_category" : one of ["HIGH", "MEDIUM", "LOW"]
  - "keywords"      : list of strings, key legal terms in this clause

Populate GCC_RULES with at least 25 realistic Railway GCC clauses
covering these categories:
  - Payment terms and milestones
  - Termination conditions (by employer and by contractor)
  - Delay penalties and liquidated damages
  - Force majeure
  - Dispute resolution and arbitration
  - Scope of work and variations
  - Insurance and indemnity
  - Defects liability period
  - Price escalation (IEEMA / WPI clauses)
  - Performance bank guarantee
  - Mobilization advance and recovery
  - Sub-contracting restrictions
  - Governing law and jurisdiction

--- FILE: core/ocr_engine.py ---

Create a class called PDFExtractor with these methods:

1. extract(pdf_path: str) -> dict
   - First attempts PyMuPDF extraction on every page
   - If a page yields fewer than 50 characters of text,
     it is classified as a scanned page
   - Scanned pages are rasterized to 300 DPI images using PyMuPDF's
     get_pixmap() and then processed with pytesseract
   - Returns a dict: {
       "full_text": str,           ← all pages joined
       "page_count": int,
       "method_used": str,         ← "digital", "ocr", or "mixed"
       "pages": list[dict]         ← per-page breakdown
     }

2. chunk_text(full_text: str, chunk_size: int = 500,
              overlap: int = 50) -> list[str]

   This method must use a TWO-STAGE chunking strategy:

   STAGE 1 — Smart Header-Based Chunking (always attempt this first):
     - Scan full_text for Railway contract section header patterns
       using regex.
     - The regex must detect these formats:
         "Clause 47", "CLAUSE 47", "47.", "47.1", "47.1.2",
         "Section 12", "SECTION 12", "Article 5", "ARTICLE 5"
     - If 5 or more such headers are found in the document:
         - Split the text at each detected header boundary
         - Each resulting segment becomes one chunk
         - Prepend the header text to the start of each chunk
           so the LLM always knows which clause it is reading
         - Skip any segment shorter than 80 words
           (these are usually blank pages or page number lines)
         - Log: "Header-based chunking: found N clause segments"
         - Return the list of clause segments directly.
           Do NOT apply further word-count splitting to these.

   STAGE 2 — Fallback Word-Count Chunking (only if Stage 1 finds
   fewer than 5 headers, meaning the PDF has no standard structure):
     - Split full_text into overlapping chunks of chunk_size words
     - Overlap of `overlap` words between consecutive chunks
       ensures clauses at boundaries are not split mid-sentence
     - Log: "Fallback word-count chunking: produced N chunks"
     - Return list of chunk strings

   The reason for this two-stage approach: a 50-page Railway GCC
   contract typically has 15-25 numbered clauses. Header-based
   chunking reduces this to 15-25 Groq API calls instead of
   80+ word-count chunks, cutting total processing time by ~70%.

Handle all exceptions. If a page fails OCR, log the error and continue
with the next page. Never crash the entire extraction because one page
failed.

--- FILE: core/vector_store.py ---

Create a class called GCCVectorStore with these methods:

1. __init__(self, persist_dir: str = "./chroma_db")
   - Initializes a ChromaDB PersistentClient at persist_dir
   - Loads the sentence-transformers model "all-MiniLM-L6-v2"
   - Gets or creates a collection named "gcc_rules"

2. is_populated(self) -> bool
   - Returns True if the collection has more than 0 documents

3. populate(self, gcc_rules: list[dict]) -> None
   - Only runs if is_populated() is False
   - Embeds each rule's clause_text using the sentence-transformers model
   - Upserts all rules into ChromaDB with:
       ids = clause_id values
       embeddings = computed embeddings
       documents = clause_text values
       metadatas = all other fields (clause_id, clause_title,
                   risk_category, keywords joined as string)

4. query(self, query_text: str, n_results: int = 3) -> list[dict]
   - Embeds query_text
   - Queries ChromaDB for top n_results matches
   - Returns a list of metadata dicts for the matched clauses

--- FILE: core/groq_client.py ---

Create a class called GroqAnalyzer with these methods:

1. __init__(self)
   - Reads GROQ_API_KEY from environment variables
   - Sets base URL to "https://api.groq.com/openai/v1/chat/completions"
   - Sets model to "llama3-70b-8192"
   - Sets max_tokens to 2048

2. analyze_clause(self, extracted_chunk: str,
                  matched_gcc_rules: list[dict]) -> dict
   - Builds a detailed system prompt that instructs the LLM to act
     as a senior Railway contract legal expert
   - Builds a user prompt that contains:
       SECTION A: The extracted clause text from the uploaded PDF
       SECTION B: The matching official GCC rules retrieved from the DB
   - Instructs the LLM to respond in this exact JSON format:
     {
       "risk_level": "HIGH" | "MEDIUM" | "LOW" | "COMPLIANT",
       "summary": "one paragraph plain English summary",
       "deviations": ["list", "of", "specific", "deviations found"],
       "recommendations": ["list", "of", "actionable", "fixes"],
       "relevant_clause_ids": ["GCC-X.X", "GCC-X.X"]
     }
   - Makes the API call using the requests library (not openai SDK)
   - Parses and returns the JSON response
   - On any API error or JSON parse failure, returns a safe error dict
     instead of crashing

3. analyze_clauses_batch(self, batch: list[dict]) -> list[dict]

   THIS IS THE PRIMARY METHOD. Use this instead of calling
   analyze_clause() in a loop one by one.

   - `batch` is a list of dicts, each with:
       {
         "chunk_text": str,          ← the extracted clause text
         "chunk_label": str,         ← e.g. "Clause 47" or "Chunk 3"
         "matched_rules": list[dict] ← GCC rules from ChromaDB query
       }
   - Accepts up to 3 items per batch (never more than 3)
   - Builds a single combined prompt containing ALL chunks in the
     batch, clearly separated like this:

       === CLAUSE 1: Clause 47 (Termination) ===
       [clause text here]
       [matched GCC rules here]

       === CLAUSE 2: Clause 52 (Payment) ===
       [clause text here]
       [matched GCC rules here]

       === CLAUSE 3: Clause 61 (Arbitration) ===
       [clause text here]
       [matched GCC rules here]

   - Instructs the LLM to respond with a JSON array of exactly
     N objects (one per clause in the batch), in the same order,
     each using the same single-clause format as analyze_clause()
   - Makes ONE Groq API call for the entire batch
   - Parses the JSON array response
   - If parsing fails for the entire batch, falls back to calling
     analyze_clause() individually for each item in the batch
   - Returns list of analysis dicts (same format as analyze_clause)

   WHY THIS EXISTS: The Groq free tier allows roughly 3 API calls
   per minute at ~1800 tokens each (6000 token/min limit).
   Batching 3 clauses per call reduces a 20-clause contract from
   20 API calls (7 minutes) down to 7 API calls (~2.5 minutes).
   Always use this method in the pipeline, not analyze_clause().

4. summarize_full_report(self, all_analyses: list[dict]) -> str
   - Takes the list of all clause analysis results
   - Calls Groq to produce a single executive summary paragraph
   - Returns it as a plain string

--- FILE: core/report_generator.py ---

Create a class called ReportBuilder with these methods:

1. __init__(self)
   - Sets up ReportLab styles, fonts, and color palette:
       HIGH risk   → red (#C0392B)
       MEDIUM risk → orange (#E67E22)
       LOW risk    → yellow (#F1C40F)
       COMPLIANT   → green (#27AE60)

2. build(self, analyses: list[dict], executive_summary: str,
         pdf_filename: str, output_path: str) -> str
   - Creates a multi-page PDF report at output_path
   - Page 1: Cover page with title "GCC Compliance Risk Report",
             original filename, date generated, overall risk score
   - Page 2: Executive Summary (the string from summarize_full_report)
   - Page 3+: One section per clause analysis containing:
       - Clause number and risk badge (color-coded)
       - Summary paragraph
       - Deviations as a bullet list
       - Recommendations as a numbered list
       - Matched GCC clause IDs
   - Final page: Disclaimer stating this is AI-generated analysis
                 and should be reviewed by a qualified legal expert
   - Returns the output_path string

--- FILE: app.py ---

Build the main Gradio application. Structure it as follows:

SECTION 1 - INITIALIZATION:
  - Load .env file
  - Initialize GCCVectorStore
  - Call vector_store.populate(GCC_RULES) on startup
  - Initialize GroqAnalyzer and ReportBuilder

SECTION 2 - CORE PIPELINE FUNCTION:
  Create a function called analyze_contract(pdf_file, progress=gr.Progress())
  that runs the full pipeline:

  Step 1 (10%): "Extracting text from PDF..."
    - Call PDFExtractor().extract(pdf_file.name)
    - Show extraction method (digital/OCR/mixed) in status

  Step 2 (30%): "Chunking document into clauses..."
    - Call chunk_text() on the extracted full_text
    - Log number of chunks found and which chunking method was used
      (header-based or word-count fallback)

  Step 3 (50%): "Querying GCC rules database..."
    - For each chunk, call vector_store.query(chunk, n_results=3)
    - Deduplicate matched rules across all chunks
    - Only process chunks that matched at least 1 rule
      (skip generic preamble/boilerplate chunks)

  Step 4 (70%): "Analyzing clauses with Groq AI (batched)..."
    - Group the relevant chunks into batches of 3 using this logic:
        batches = []
        for i in range(0, len(relevant_chunks), 3):
            batches.append(relevant_chunks[i:i+3])

    - For each batch:
        - Build the batch input list:
            each item = {
              "chunk_text": chunk_text,
              "chunk_label": detected header label OR "Chunk N",
              "matched_rules": that chunk's matched GCC rules
            }
        - Call groq_analyzer.analyze_clauses_batch(batch)
        - Extend all_analyses list with the returned results
        - Update progress bar incrementally per batch, not per clause
        - Add a 1.2-second delay BETWEEN batches (not between clauses)
          to stay within Groq's rate limits

    - Update status: "Analyzed X clauses in Y batches.
                      Estimated time saved vs unbatched: Z seconds"
      where Z = (total_clauses - total_batches) * 18 seconds

    - If the total number of relevant chunks exceeds 30:
        Show a warning in the status box:
        "⚠️ Large contract detected (30+ clauses).
         Analysis will take approximately X minutes."
        where X = ceil(total_batches * 1.5)

  Step 5 (85%): "Generating executive summary..."
    - Call groq_analyzer.summarize_full_report(all_analyses)

  Step 6 (95%): "Building PDF report..."
    - Call report_builder.build() with a temp output path
    - Return path to the generated PDF

  Step 7 (100%): "Done."
    - Return: (status_message, report_stats_markdown, pdf_file_path)

  report_stats_markdown should be a Gradio Markdown string showing:
    - Total clauses analyzed
    - Risk breakdown table (HIGH / MEDIUM / LOW / COMPLIANT counts)
    - Extraction method used (digital / OCR / mixed)
    - Chunking method used (header-based / word-count fallback)
    - Number of GCC rules matched

SECTION 3 - GRADIO UI:
  Build the UI using gr.Blocks() with a clean, professional theme.
  Use gr.themes.Soft() as the base theme.

  Layout:
  - Header: App title and one-line description
  - Row 1: File upload component (accepts PDF only, max 50MB)
  - Row 2: "Analyze Contract" button (primary color)
  - Row 3: Status textbox (shows live progress messages)
  - Row 4: Stats markdown panel (shows risk breakdown after analysis)
  - Row 5: Download button for the PDF report
           (hidden until analysis completes, then becomes visible)
  - Footer: Small disclaimer text

  Wire the button click to analyze_contract().
  Use gr.Progress() for the progress bar.
  On error, display the error message in the status box instead of crashing.

SECTION 4 - LAUNCH:
  Launch with:
    demo.launch(
      auth=[("admin", os.getenv("APP_PASSWORD", "gcc2024"))],
      share=False,
      server_name="0.0.0.0",
      server_port=7860
    )

--- FILE: requirements.txt ---

List every dependency with a pinned version that is stable and
compatible with Python 3.10 (which Hugging Face Spaces CPU Basic uses):

Include: gradio, pymupdf, pytesseract, Pillow, chromadb,
sentence-transformers, reportlab, python-dotenv, requests,
torch (cpu-only version), transformers, numpy

--- FILE: .env.example ---

GROQ_API_KEY=your_groq_api_key_here
APP_PASSWORD=your_chosen_password_here

--- FILE: README.md ---

Write a complete README with these sections:
1. What this app does (3 sentences)
2. Local setup instructions (step by step, macOS terminal commands)
3. How to get a free Groq API key (with the URL: https://console.groq.com)
4. How to deploy to Hugging Face Spaces (step by step):
   - Create a new Space (Gradio SDK, CPU Basic hardware)
   - Add GROQ_API_KEY and APP_PASSWORD as Space Secrets
   - Push the code via git
5. First-run behavior (ChromaDB populates on first launch, takes ~60s)
6. Known limitations (sleep after 48h, OCR speed on scanned docs,
   Groq rate limits on free tier)

=======================================================================
ADDITIONAL CONSTRAINTS AND QUALITY REQUIREMENTS
=======================================================================

1. NEVER use the openai Python SDK. Use the requests library for all
   Groq API calls. The Groq API is OpenAI-compatible but I want
   explicit requests calls so the code is transparent.

2. ALL environment variables must be read via os.getenv() with safe
   fallback defaults where appropriate.

3. Every class and function must have a docstring.

4. All file I/O must use context managers (with open(...) as f).

5. ChromaDB must use PersistentClient so the vector index survives
   Hugging Face Space restarts (it is stored in the Space's
   persistent disk, not in memory).

6. The Gradio progress bar MUST update at each step. Do not batch
   all updates at the end.

7. The PDF report output must be saved to /tmp/ directory
   (writable on HF Spaces) with a timestamped filename like:
   gcc_report_20240615_143022.pdf

8. Handle the case where PyMuPDF extracts garbled text from a
   heavily formatted PDF — if the extracted text contains fewer
   than 30% alphabetic characters, treat that page as a scanned
   page and re-run OCR on it.

9. The sentence-transformers model must be downloaded at startup,
   not on first query, so the first user does not experience a delay.

10. Add a check: if the uploaded file is not a valid PDF
    (check magic bytes, not just extension), return an error message
    immediately without attempting extraction.

11. CHUNKING PRIORITY: Header-based chunking is always the preferred
    method. The word-count fallback exists only for contracts that
    have no standard clause numbering. Log which method was used
    and display it in the stats panel after analysis completes.

12. BATCH SIZE HARD LIMIT: Never send more than 3 clauses in a
    single Groq batch call. At 3 clauses per call, the combined
    prompt stays safely under 4096 input tokens even for
    verbose Railway GCC clauses. Sending 4 or more risks hitting
    the context window limit and returning a malformed response.

13. BATCH FALLBACK MUST WORK: If the batch JSON response cannot be
    parsed (LLM returned markdown, extra text, or malformed JSON),
    the fallback to individual analyze_clause() calls must be
    automatic and silent. The user should never see a batch
    parsing error — they should just get correct results slightly
    slower.

=======================================================================
START BY GENERATING THE FILES IN THIS ORDER:
=======================================================================

1. data/gcc_rules.py         ← needed by everything else
2. requirements.txt          ← needed to understand available libs
3. core/__init__.py          ← empty, just creates package
4. core/ocr_engine.py
5. core/vector_store.py
6. core/groq_client.py
7. core/report_generator.py
8. app.py                    ← depends on all core modules
9. .env.example
10. README.md

Generate every file completely. Do not truncate any file.
Do not say "add the rest of the code here".
Every function must be fully implemented.
```

---

## Expected Processing Times (for reference)

| Scenario | Estimated Time |
|---|---|
| Digital PDF, 50 pages, app awake | ~2–3 minutes |
| Scanned PDF, 50 pages, app awake | ~9–12 minutes |
| Digital PDF + cold start (app was sleeping) | ~5–6 minutes |
| Scanned PDF + cold start | ~12–15 minutes |

**Key insight:** Groq's free tier caps at ~6,000 tokens/minute.
Batching 3 clauses per call reduces a 20-clause contract from
20 API calls (~7 min) down to 7 batched calls (~2.5 min).

---

## What Was Changed From Original Prompt

- `chunk_text()` in `ocr_engine.py` — replaced with **two-stage chunking**
  (header-based first, word-count fallback second)
- `groq_client.py` — added `analyze_clauses_batch()` as the primary method;
  `analyze_clause()` demoted to fallback only
- Step 4 in `app.py` — now groups chunks into batches of 3 before calling Groq
- Stats panel now shows chunking method used
- Constraints 11, 12, 13 added covering chunking priority, batch size hard
  limit, and silent fallback behaviour
