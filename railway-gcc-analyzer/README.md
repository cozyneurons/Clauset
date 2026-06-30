# Railway GCC Contract Risk Analyzer

## What This App Does

This web application allows users to upload a PDF Railway contract (up to 100 pages), automatically extract and analyse its clauses against the official Indian Railways General Conditions of Contract (GCC) rule database using AI, and download a detailed, colour-coded risk report. The system uses semantic search (ChromaDB + sentence-transformers) to match contract clauses against 25+ GCC rules and an LLM (Groq / LLaMA 3-70B) to identify deviations, risks, and actionable recommendations. The generated PDF report includes an executive summary, per-clause risk ratings (HIGH / MEDIUM / LOW / COMPLIANT), specific deviations found, and recommended fixes.

---

## Local Setup Instructions (macOS)

Follow these steps to run the app on your local Mac:

```bash
# 1. Clone or download this repository into a directory
git clone <your-repo-url> railway-gcc-analyzer
cd railway-gcc-analyzer

# 2. Create and activate a Python 3.10 virtual environment
python3.10 -m venv .venv
source .venv/bin/activate

# 3. Install Tesseract OCR (required for scanned PDFs)
brew install tesseract

# 4. Install all Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 5. Create your .env file from the example template
cp .env.example .env

# 6. Open .env in a text editor and fill in your credentials
#    (see the 'How to get a Groq API key' section below)
nano .env

# 7. Run the application
python app.py
```

The app will start at **http://localhost:7860**. Log in with:
- **Username:** `admin`
- **Password:** the value of `APP_PASSWORD` in your `.env` file (default: `gcc2024`)

---

## How to Get a Free Groq API Key

1. Visit **https://console.groq.com**
2. Sign up for a free account (no credit card required)
3. Navigate to **API Keys** in the left sidebar
4. Click **Create API Key**, give it a name, and copy the key
5. Paste it as the value of `GROQ_API_KEY` in your `.env` file

> **Free tier limits:** approximately 6,000 tokens per minute and 14,400 tokens per day on the `llama3-70b-8192` model. The app's batching strategy (3 clauses per API call) is specifically designed to stay within these limits.

---

## How to Deploy to Hugging Face Spaces

### Step 1 — Create a new Space

1. Go to **https://huggingface.co/spaces**
2. Click **Create new Space**
3. Fill in:
   - **Space name:** `railway-gcc-analyzer` (or any name you like)
   - **SDK:** `Gradio`
   - **Hardware:** `CPU Basic` (free tier)
   - **Visibility:** Public or Private
4. Click **Create Space**

### Step 2 — Add Secrets

In your Space settings, go to **Settings → Variables and Secrets** and add:

| Secret Name | Value |
|-------------|-------|
| `GROQ_API_KEY` | Your Groq API key from https://console.groq.com |
| `APP_PASSWORD` | A password for the Gradio login screen |

Secrets are stored encrypted and are injected as environment variables at runtime.

### Step 3 — Push the code

```bash
# In your local project directory:

# Add the HuggingFace Space as a remote
git remote add space https://huggingface.co/spaces/<your-username>/railway-gcc-analyzer

# Push all files
git add .
git commit -m "Initial deployment"
git push space main
```

> **Tip:** You must have `git-lfs` installed for large files. Run `git lfs install` before pushing if you encounter issues with large model files.

The Space will automatically build, install dependencies from `requirements.txt`, and launch `app.py`.

---

## First-Run Behaviour

On the **very first launch** (local or on HF Spaces), the following happens automatically:

1. **Sentence-transformers model download** (~90 MB): The `all-MiniLM-L6-v2` model is downloaded from Hugging Face Hub and cached locally. This takes approximately 30–60 seconds on first run.
2. **ChromaDB population** (~5–10 seconds): All 25+ GCC rules are embedded and inserted into the local ChromaDB vector database at `./chroma_db/`. On subsequent launches, ChromaDB detects existing data and skips this step instantly.
3. **Total cold-start time:** approximately 60–90 seconds.

After the first launch, subsequent starts are much faster (model is cached, ChromaDB is pre-populated).

---

## Expected Processing Times

| Scenario | Estimated Time |
|----------|---------------|
| Digital PDF, 20–50 pages, app warm | ~2–3 minutes |
| Scanned PDF, 20–50 pages, app warm | ~9–12 minutes |
| Digital PDF + cold start | ~5–6 minutes |
| Scanned PDF + cold start | ~12–15 minutes |

The app uses **batched LLM calls** (3 clauses per Groq API call) which reduces processing time by approximately 70% compared to individual clause analysis.

---

## Known Limitations

| Limitation | Details |
|------------|---------|
| **HF Space sleep** | Free-tier Spaces sleep after 48 hours of inactivity. The next request triggers a cold start (~60–90s). |
| **OCR speed** | Scanned PDFs (no digital text layer) require pytesseract OCR at 300 DPI per page, which takes 8–15 seconds per page on CPU. A 50-page scanned contract can take 10–15 minutes. |
| **Groq free-tier rate limits** | The free Groq API is limited to ~6,000 tokens/minute and ~14,400 tokens/day. Very large contracts (50+ clauses) may hit this limit and slow analysis. |
| **PDF size** | Files larger than 50 MB may cause memory issues on the CPU Basic hardware tier. |
| **Language** | OCR is configured for English. Contracts with significant Hindi or regional language content may have lower OCR accuracy. |
| **AI accuracy** | LLM-based analysis may produce errors or misinterpretations. All outputs must be reviewed by a qualified legal expert. |
| **GCC version** | The embedded GCC rules are based on the standard Indian Railways GCC. Project-specific Special Conditions of Contract (SCC) that override GCC clauses are not included in the database. |
