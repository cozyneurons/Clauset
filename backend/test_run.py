import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Resolve everything relative to this script file, not the working directory
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)
sys.path.insert(0, str(SCRIPT_DIR))

load_dotenv(SCRIPT_DIR / ".env")

from core.agents.pipeline import ContractAnalysisPipeline

logging.basicConfig(level=logging.INFO)

GCC_CLAUSES_PATH = SCRIPT_DIR / "data" / "gcc_clauses.json"
with open(GCC_CLAUSES_PATH, "r", encoding="utf-8") as f:
    gcc_clauses = json.load(f)

PDF_PATH = SCRIPT_DIR.parent / "railway_contract_test.pdf"
OUTPUT_PATH = SCRIPT_DIR / "test_result.json"

pipeline = ContractAnalysisPipeline()

def on_event(event):
    print(f"[{event.agent}] {event.status} - {event.message} ({event.progress}%)")

print(f"Starting analysis on {PDF_PATH}...")
try:
    result = pipeline.run({
        "pdf_path": str(PDF_PATH),
        "filename": "railway_contract_test.pdf",
        "gcc_clauses": gcc_clauses,
    }, emit=on_event)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\nAnalysis complete! Results saved to {OUTPUT_PATH}")
    print(f"Found: {result['found_count']}")
    print(f"Missing: {result['missing_count']}")
    print(f"Needs Review: {result['needs_review_count']}")
    print(f"Gemini Summary: {json.dumps(result['gemini_summary'], indent=2)}")
except Exception as e:
    import traceback
    print(f"Error during execution: {e}")
    traceback.print_exc()
