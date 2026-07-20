import os
import json
import time
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")

# Initialize the Gemini client
client = genai.Client(api_key=api_key)

def call_with_backoff(func, *args, **kwargs):
    """
    Executes a function with exponential backoff retry logic.
    Particularly useful for handling rate limit (429) errors.
    """
    max_retries = 6
    base_delay = 2.0
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            delay = base_delay * (2 ** attempt)
            print(f"\n[Warning] Call failed: {e}. Retrying in {delay:.1f} seconds (attempt {attempt + 1}/{max_retries})...")
            time.sleep(delay)

def main():
    chunks_path = "chunks.json"
    output_path = "vector_index.json"

    if not os.path.exists(chunks_path):
        raise FileNotFoundError(f"Source file '{chunks_path}' not found. Run chunk_paragraphs.py first.")

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    total_chunks = len(chunks)
    print(f"Loaded {total_chunks} chunks from '{chunks_path}'. Generating embeddings...")

    vector_index = []
    
    # We use a 1.5s base sleep to stay comfortably below rate limits, 
    # and combine it with call_with_backoff to handle any unexpected rate limits.
    for idx, chunk in enumerate(chunks, 1):
        para_id = chunk.get("para_id")
        source = chunk.get("source")
        text = chunk.get("text", "").strip()
        version = chunk.get("version", "v1")

        if not text:
            print(f"[{idx}/{total_chunks}] Skipping empty text for para_id: {para_id}")
            continue

        # Get embedding with exponential backoff support
        result = call_with_backoff(
            client.models.embed_content,
            model="gemini-embedding-001",
            contents=text
        )
        
        embedding = result.embeddings[0].values
        
        vector_index.append({
            "para_id": para_id,
            "source": source,
            "text": text,
            "version": version,
            "embedding": embedding
        })
        
        print(f"Embedded {idx}/{total_chunks} (para_id: {para_id})")
        
        # Respect API rate limits
        time.sleep(1.5)

    # Save to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(vector_index, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully built index! Saved {len(vector_index)} embedded chunks to '{output_path}'.")

if __name__ == "__main__":
    main()
