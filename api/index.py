import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS
from check_script import check_script
from diff_script import diff_script

app = Flask(__name__)
CORS(app)  # allows a browser-based frontend to call this later

@app.route("/api/check-script", methods=["POST"])
def check_script_endpoint():
    data = request.get_json(force=True)

    script_text = data.get("script_text")
    loan_type = data.get("loan_type")
    version = data.get("version", "v1")

    if not script_text or not loan_type:
        return jsonify({"error": "script_text and loan_type are required fields"}), 400

    try:
        results = check_script(script_text, loan_type, version)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/diff-script", methods=["POST"])
def diff_script_endpoint():
    data = request.get_json(force=True)

    script_text = data.get("script_text")
    loan_type = data.get("loan_type")

    if not script_text or not loan_type:
        return jsonify({"error": "script_text and loan_type are required fields"}), 400

    try:
        result = diff_script(script_text, loan_type)
        return jsonify({"diff": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500