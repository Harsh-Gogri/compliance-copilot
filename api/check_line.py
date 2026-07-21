from sys import version
import os
import json
import math
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_INDEX_PATH = os.path.join(BASE_DIR, "..", "vector_index.json")

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")

# Initialize the Gemini client
client = genai.Client(api_key=api_key)

# Pydantic schema for structured JSON output
class ComplianceCheck(BaseModel):
    status: str = Field(
        description="Classification of the line: 'green' (compliant), 'amber' (borderline/warning), or 'red' (non-compliant)."
    )
    source: Optional[str] = Field(
        None,
        description="The document source of the compliance rules (e.g. '2025 Directions', '2010 Recovery Agent Guidelines') if applicable. Set to null if no retrieved paragraph is genuinely relevant."
    )
    para_id: Optional[str] = Field(
        None,
        description="The specific para_id(s) of the compliance rules (e.g. '91', '100', '2.4.2(v)(c)') if applicable. Set to null if no retrieved paragraph is genuinely relevant."
    )
    explanation: str = Field(
        description="Exactly one sentence explaining why the line was classified this way. For green-status lines where no rule is relevant, state that the line is clean and no specific restrictions apply rather than inventing a compliance rationale."
    )
    rewrite: str = Field(
        description="A suggested compliant rewrite of the line if status is amber or red. If status is green, this should be empty or the original text."
    )

# Vector helpers for cosine similarity
def dot_product(v1, v2):
    return sum(x * y for x, y in zip(v1, v2))

def magnitude(v):
    return math.sqrt(sum(x * x for x in v))

def cosine_similarity(v1, v2):
    m1 = magnitude(v1)
    m2 = magnitude(v2)
    if m1 == 0 or m2 == 0:
        return 0.0
    return dot_product(v1, v2) / (m1 * m2)

# Some RBI paragraphs apply differently depending on loan type.
# Any paragraph not listed here applies regardless of loan type.
LOAN_TYPE_SCOPE = {
    "89": "microfinance",
    "90": "microfinance",
    "91": "microfinance",
    "92": "microfinance",
    "100": "general",
}

def retrieve_top_chunks(query, version, loan_type, index_path=VECTOR_INDEX_PATH, top_n=12):
    # Embed query
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=query
    )
    query_emb = result.embeddings[0].values

    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)
    print(f"[DEBUG] Loaded {len(index)} chunks from {index_path}")
    print(f"[DEBUG] para_id=100 present in raw loaded index: {any(c['para_id'] == '100' for c in index)}")

    # Filter chunks by version
    filtered_index = [chunk for chunk in index if chunk.get("version") == version]
    if not filtered_index:
        print(f"[Warning] No chunks found for version '{version}'. Defaulting to all chunks.")
        filtered_index = index
    
    print(f"[DEBUG] After version filter: para_id=100 present: {any(c['para_id'] == '100' for c in filtered_index)}")
    print(f"[DEBUG] repr(loan_type) = {repr(loan_type)}")
    print(f"[DEBUG] LOAN_TYPE_SCOPE.get('100') = {repr(LOAN_TYPE_SCOPE.get('100'))}")
    print(f"[DEBUG] Condition result: {LOAN_TYPE_SCOPE.get('100') in (None, loan_type)}")

    # Filter out chunks scoped to a different loan type
    filtered_index = [
        chunk for chunk in filtered_index
        if LOAN_TYPE_SCOPE.get(chunk["para_id"]) in (None, loan_type)
    ]

    print(f"[DEBUG] After loan_type filter: para_id=100 present: {any(c['para_id'] == '100' for c in filtered_index)}")

    scored = []
    for chunk in filtered_index:
        sim = cosine_similarity(query_emb, chunk["embedding"])
        scored.append({
            "para_id": chunk["para_id"],
            "source": chunk["source"],
            "text": chunk["text"],
            "similarity": sim
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)

    print(f"[DEBUG] In scored (all, unsliced): para_id=100 present: {any(c['para_id'] == '100' for c in scored)}")

    top_chunks = scored[:top_n]

    # Guarantee the definitive threshold paragraph for this loan type is always
    # included, even if it didn't rank in the top_n by similarity alone.
    anchor_para_id = (
        "91" if loan_type == "microfinance"
        else "100" if loan_type == "general"
        else None
    )

    if anchor_para_id and not any(c["para_id"] == anchor_para_id for c in top_chunks):
        anchor_chunk = next(
            (c for c in scored if c["para_id"] == anchor_para_id),
            None
        )
        if anchor_chunk:
            top_chunks.append(anchor_chunk)

    return top_chunks

def check_line(line, loan_type, version):
    # Step 1: Retrieve context
    top_chunks = retrieve_top_chunks(line, version, loan_type)
    print(f"[{loan_type}/{version}] {line[:40]}.. Retrieved: {[c['para_id'] for c in top_chunks]}")
    
    # Format the retrieved context for the prompt
    context_str = ""
    for idx, chunk in enumerate(top_chunks, 1):
        context_str += f"[{idx}] Source: {chunk['source']} | para_id: {chunk['para_id']}\nText: {chunk['text']}\n\n"

    # Step 2: Build the prompt with loan type constraints
    prompt = f"""You are a compliance assistant specializing in Non-Banking Financial Company (NBFC) and banking regulations in India.

Evaluate the following candidate communication line for regulatory compliance based on the provided reference contexts and the specified loan type.

Loan Type:
{loan_type}

Candidate Line to Check:
"{line}"

Reference Compliance Contexts:
{context_str}

CRITICAL RULES INSTRUCTIONS:
- You must evaluate the line strictly based on the reference compliance contexts retrieved above, for the stated loan type.
- Do not apply rules from any paragraph not shown in the reference contexts above.
- If the retrieved contexts do not address a particular loan type distinction explicitly, apply the rule as generally stated.
- If the candidate line mentions a specific time, always prioritize citing a reference paragraph that states an explicit numeric time threshold (e.g. "before 9:00 a.m." or "after 6:00 p.m.") over a paragraph that only generally mentions "hours of calling" without stating a specific cutoff, such as training or sensitivity requirements. Use the paragraph with the explicit threshold to determine compliance status.

Instructions:
1. Classify the candidate line as 'green' (fully compliant), 'amber' (suspect, borderline, or warning), or 'red' (violating a rule or highly non-compliant).
2. Cite the specific reference source and `para_id` you based this on. IMPORTANT:
   - For green-status lines, only include source and para_id if a specific retrieved paragraph directly and clearly relates to the content of the line.
   - If no retrieved paragraph is genuinely relevant, set BOTH `source` and `para_id` to null.
   - If a citation applies, populate BOTH `source` and `para_id` together.
3. Write a single-sentence explanation of your reasoning. IMPORTANT: For green-status lines where no compliance rule is relevant, state that the line is clean and no specific restrictions apply. Do not invent a compliance rationale if no rule actually applies.
4. Suggest a compliant alternative rewrite if the classification is amber or red.
"""

    # Step 3: Call Gemini with Structured Outputs
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ComplianceCheck,
        temperature=0.0
    )

    response = client.models.generate_content(
        model="gemini-flash-lite-latest",
        contents=prompt,
        config=config
    )

    return response.text

def main():
    test_line = "We will call you again at 6:30pm if we don't hear back."
    
    # Run test 1: Microfinance
    print(f"Test 1: Checking line: '{test_line}' with loan_type='microfinance', version='v1'")
    print("Running compliance check...")
    res_micro = check_line(test_line, loan_type="microfinance", version="v1")
    parsed_micro = json.loads(res_micro)
    print("\nMicrofinance Compliance Output JSON:")
    print("=" * 80)
    print(json.dumps(parsed_micro, indent=2))
    print("=" * 80)
    print("\n" + "#" * 80 + "\n")

    # Run test 2: General
    print(f"Test 2: Checking line: '{test_line}' with loan_type='general', version='v1'")
    print("Running compliance check...")
    res_general = check_line(test_line, loan_type="general", version="v1")
    parsed_general = json.loads(res_general)
    print("\nGeneral Compliance Output JSON:")
    print("=" * 80)
    print(json.dumps(parsed_general, indent=2))
    print("=" * 80)

if __name__ == "__main__":
    main()
