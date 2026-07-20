import json
import re
import time
from check_line import check_line

def check_script(script_text, loan_type, version):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script_text.strip()) if s.strip()]

    print(f"Split script into {len(sentences)} sentences. Checking each sentence...")

    results = []
    for idx, sentence in enumerate(sentences, 1):
        print(f"[{idx}/{len(sentences)}] Processing: '{sentence}'")

        attempt = 0
        while attempt < 2:
            try:
                json_str = check_line(sentence, loan_type, version)
                result_dict = json.loads(json_str)
                full_result = {"sentence": sentence}
                full_result.update(result_dict)
                results.append(full_result)
                break
            except Exception as e:
                if "429" in str(e) and attempt == 0:
                    print(f"Rate limited, waiting 20s before retry...")
                    time.sleep(20)
                    attempt += 1
                    continue
                print(f"Error checking sentence '{sentence}': {e}")
                results.append({
                    "sentence": sentence,
    "status": "error",
    "source": None,
    "para_id": None,
    "explanation": "Couldn't complete this check, likely a temporary rate limit. Try running the script again in a moment.",
    "rewrite": ""
                })
                break

        time.sleep(4.5)  # stay under the 15-requests-per-minute free tier cap

    return results


def main():
    test_script = (
        "Good evening, this is regarding your overdue loan account. "
        "We will call you again at 6:30pm today if we don't hear back. "
        "We're happy to discuss a revised repayment plan that works for you."
    )
    results = check_script(test_script, loan_type="microfinance", version="v1")
    print("\nFinal results:")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()