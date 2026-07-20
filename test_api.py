import requests
import json

response = requests.post(
    "http://127.0.0.1:5000/diff-script",
    json={
        "script_text": (
            "Good evening, this is regarding your overdue loan account. "
            "We will call you again at 6:30pm today if we don't hear back. "
            "We're happy to discuss a revised repayment plan that works for you."
        ),
        "loan_type": "microfinance"
    }
)

print(response.status_code)
print(json.dumps(response.json(), indent=2))