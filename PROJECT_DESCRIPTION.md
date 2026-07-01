# Railway GCC Contract Analyzer - Project Description

The **Railway GCC Contract Analyzer** is an AI-powered system designed to analyze Indian Railways contract PDFs. It compares the contents of a given contract against the standard library of the General Conditions of Contract (GCC). 

The backend is built with **FastAPI** and uses a multi-agent architecture powered by **Google Gemini** (for initial mapping) and optionally **Gemini** (for secondary validation).

---

## Key Features

1. **Intelligent Text Extraction**: Processes uploaded PDF contracts using PyMuPDF, falling back to Tesseract OCR when dealing with scanned or non-selectable text.
2. **AI-Powered Clause Mapping**: Uses Google's Gemini models to intelligently map sections of the contract text to standard GCC clauses, extracting verbatim start and end anchors.
3. **Multi-Part Processing**: Automatically chunks large contracts into multiple parts to bypass token limits while maintaining context during the LLM mapping phase.
4. **Fuzzy Fallback Search**: Implements a robust keyword-based fuzzy search using RapidFuzz. If Gemini misses a clause, this fallback mechanism scans the full contract text to determine if the clause is genuinely missing or if it's hidden under different verbiage.
5. **Precise Verbatim Extraction**: Maps the LLM's returned anchors back to the exact character coordinates of the original, unnormalized document text, guaranteeing perfect verbatim text extraction.
6. **Multi-Agent Architecture**: Encapsulates discrete steps into isolated agents (`DocumentAgent`, `MapperAgent`, `ValidatorAgent`, `GeminiValidatorAgent`) for clean separation of concerns.
7. **Second-Pass Validation (Optional)**: Can route the extracted clauses through a Gemini AI agent (`gemini-3.1-flash-lite`) to perform a strict validation against the official GCC text, flagging clauses that need human review.
8. **RESTful API**: Exposes clean endpoints for contract analysis and for browsing the underlying GCC clause dataset.

---

## System Architecture & Agents

The application pipeline (`ContractAnalysisPipeline`) orchestrates the flow of data through four specialized agents:

1. **`DocumentAgent`**: Responsible for the ingestion phase. It receives the PDF, extracts the raw text page-by-page, and splits the document into 3 logical parts for LLM ingestion.
2. **`MapperAgent`**: Receives the document parts and calls the Gemini API on each part. It provides the LLM with a compact metadata index of the GCC clauses, asking it to identify present clauses and return verbatim start/end anchors.
3. **`ValidatorAgent`**: Takes the anchors provided by the MapperAgent and performs fuzzy matching against the original document text to slice out the full verbatim clause text. It also identifies "missing" clauses and runs a fuzzy keyword search over the document to double-check their absence.
4. **`GeminiValidatorAgent`** *(Optional)*: If an `GEMINI_VALIDATION_ENABLED` is present, this agent acts as an auditor. It takes the output from the ValidatorAgent and runs batch validations to ensure the identified clauses truly represent the spirit of the GCC standard.

---

## Complete Application Flow (POST `/api/analyze`)

1. **Upload & Validation**: A user uploads a PDF contract via the `/api/analyze` endpoint. The file is temporarily stored on the disk.
2. **Text Extraction**: The `DocumentAgent` reads the PDF, using OCR if necessary, producing a continuous string of full text alongside structured page-by-page text.
3. **Chunking**: The document is split into 3 parts to ensure it fits within the context window limits of the LLMs without losing semantic meaning.
4. **Mapping (Gemini Phase)**: 
    - The `MapperAgent` sends 3 concurrent or sequential API requests to Gemini.
    - Gemini returns JSON objects detailing the `clause_id`, `page_number`, and `start_anchor` / `end_anchor` for every clause it identifies.
5. **Consolidation**: The responses from the 3 parts are merged, deduplicated, and missing GCC clauses are isolated into a `missing_candidates` list.
6. **Verbatim Extraction**:
    - For found clauses, the `ValidatorAgent` maps the anchors back to the original document coordinates to cleanly slice the exact text.
7. **Fuzzy Fallback Phase**:
    - For `missing_candidates`, the `ValidatorAgent` checks the full document text against the keywords associated with those clauses.
    - If enough keywords match, the clause is upgraded to `present_fuzzy`.
    - If not, it is confirmed as `truly_missing`.
8. **Second-Pass Validation Phase**:
    - If enabled, the `GeminiValidatorAgent` receives the results.
    - It evaluates whether the evidence pulled from the contract strongly aligns with the official GCC definitions.
    - Clauses with weak evidence are flagged as `needs_review`.
9. **Response Assembly**: A structured JSON payload containing the final statuses, counts, and verbatim texts is returned to the client.
10. **Cleanup**: The temporary PDF is deleted from the server.
