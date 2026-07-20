import os
from pathlib import Path
from pypdf import PdfReader

SOURCE_DIR = Path("source-docs")
OUTPUT_FILE = Path("raw_text.txt")

pdf_files = sorted(SOURCE_DIR.glob("*/*.pdf"))
if not pdf_files:
    raise FileNotFoundError(f"No PDF files found in '{SOURCE_DIR}/'")

all_text = []

for pdf_path in pdf_files:
    print(f"Extracting: {pdf_path.name}")
    reader = PdfReader(pdf_path)
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages_text.append(text)
    doc_text = "\n".join(pages_text)
    version = pdf_path.parent.name  # "v1" or "v2", from the folder name
    all_text.append(f"=== [{version}] {pdf_path.name} ===\n\n{doc_text}")

combined = "\n\n\n".join(all_text)

OUTPUT_FILE.write_text(combined, encoding="utf-8")
print(f"\nDone. Saved {len(combined):,} characters to '{OUTPUT_FILE}'")
