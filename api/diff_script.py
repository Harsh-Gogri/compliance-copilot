import json
from check_script import check_script

def diff_script(script_text, loan_type):
    current_results = check_script(script_text, loan_type, version="v1")
    draft_results = check_script(script_text, loan_type, version="v2")

    diff = []
    for current, draft in zip(current_results, draft_results):
        changed = current["status"] != draft["status"]
        diff.append({
            "sentence": current["sentence"],
            "changed": changed,
            "current": {
                "status": current["status"],
                "source": current["source"],
                "para_id": current["para_id"],
                "explanation": current["explanation"]
            },
            "draft": {
                "status": draft["status"],
                "source": draft["source"],
                "para_id": draft["para_id"],
                "explanation": draft["explanation"]
            }
        })
    return diff

def main():
    test_script = (
        "Dear borrower, this is a reminder to settle your outstanding dues. "
        "We will call you at 6:30pm tonight to collect the payment. "
        "Failure to repay will result in immediate public notification of your relatives."
    )
    result = diff_script(test_script, loan_type="microfinance")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()