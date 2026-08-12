# Compliance Copilot

Compliance Copilot is an automated compliance auditing tool designed to evaluate call center agent scripts against Reserve Bank of India (RBI) regulatory frameworks. Most existing script-adherence tools check whether a telecalling or recovery agent strictly follows an internally approved script, but they leave a critical vulnerability unaddressed: verifying whether the approved script itself remains compliant with evolving regulations. Compliance Copilot solves this problem by auditing agent script lines directly against primary regulatory texts, flagging non-compliant ("red"), borderline ("amber"), or compliant ("green") phrasing, and providing regulation-grounded rewrites.

## How It Works

The system relies on a Retrieval-Augmented Generation (RAG) architecture to maintain factual grounding and prevent artificial intelligence model hallucinations:

1. **Paragraph-Level Chunking**: Source regulatory documents are parsed and segmented into paragraph-level chunks, retaining metadata such as section headings and original paragraph numbers.
2. **Embedding & Storage**: Each regulatory paragraph is converted into a numerical vector representation using an embedding model and indexed for fast retrieval.
3. **Cosine Similarity Matching**: When an incoming script line is analyzed, it is embedded into the same vector space and compared against stored regulatory paragraphs using cosine similarity to find the most relevant rules.
4. **Grounded LLM Evaluation**: Only the top matching regulatory paragraphs are supplied to the Large Language Model alongside the script line. Because the model's context is restricted exclusively to these retrieved excerpts, it cannot fabricate or cite a rule that does not exist in the source text.

## Two Dimensions of Filtering

Compliance expectations vary significantly depending on context. To account for this, audits run across two filtering dimensions:

* **Regulation Version**:
  * **Current Regulation (v1)**: Checks scripts against active RBI Master Directions and guidelines currently enforced.
  * **Draft Amendment (v2)**: Checks scripts against proposed RBI draft guidelines under consultation, allowing lenders to test scripts against upcoming regulatory changes.
* **Loan Type**:
  * **Microfinance (MFI)**: Evaluates scripts against rules specific to microfinance borrowers (such as qualifying asset criteria, household income caps, and stringent debt recovery conduct prohibitions).
  * **General Lending**: Evaluates scripts against standard consumer and commercial lending regulations, which feature different disclosure requirements and operational thresholds.

## Tech Stack

* **Language**: Python
* **Backend Framework**: Flask, Flask-CORS
* **AI & Embeddings (Google Gemini API)**:
  * `gemini-embedding-001` for vector embedding generation
  * `gemini-flash-lite-latest` for grounded compliance classification and explanation
* **Data Validation**: Pydantic for structured JSON schema validation of model responses
* **Frontend**: Vanilla HTML, CSS, and JavaScript
* **Hosting**: Vercel

## Known Limitations

This project is a working engineering prototype built to demonstrate the RAG architecture and compliance verification concept, not a production-grade legal system:

* **Prototype Status**: Designed as a proof-of-concept for script evaluation rather than an enterprise-ready platform.
* **Source Material Integrity**: The current-regulation (v1) source documents consist of real, primary RBI texts and are cited by exact paragraph number. However, the draft-amendment (v2) content was reconstructed from secondary legal commentary and summaries because the primary RBI draft text was not publicly locatable at the time of development. Draft-amendment results should be viewed as illustrative rather than verified.
* **Retrieval Dynamics**: Retrieval accuracy has been tested across representative financial scripts. However, like any RAG system, semantic matching can occasionally surface a broader or less specific regulatory clause instead of a highly specific rule when encountering unusual or indirect phrasing.
* **No Legal Certification**: The tool does not provide legal advice, regulatory certification, or guarantee complete legal coverage.

## Running Locally

### Prerequisites

* Python 3.9+
* A Google Gemini API key

### Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd compliance-copilot
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Add environment variables**:
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

5. **Run the data pipeline scripts in sequence**:
   *(Required if regenerating chunks or re-building the vector index from source PDFs)*
   ```bash
   python extract_text.py
   python chunk_paragraphs.py
   python build_index.py
   ```

6. **Run the Flask application**:
   ```bash
   python api/index.py
   ```

7. **Open the web application**:
   Open `public/index.html` in your web browser.
