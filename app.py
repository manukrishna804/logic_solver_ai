import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not set")

genai.configure(api_key=API_KEY)

# For older SDKs, just pass model name as positional argument
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate-algorithm", methods=["POST"])
def generate_algorithm():
    data = request.json
    coding_question = data.get("coding_question")
    if not coding_question:
        return jsonify({"error": "No coding question provided"}), 400

    prompt = f"Generate a step-by-step algorithm for: '{coding_question}' (numbered list)."

    try:
        response = gemini_model.generate_content(prompt)
        # Depending on SDK, the output text may be in response.text or response.output_text
        algorithm_text = getattr(response, "text", None) or getattr(response, "output_text", None)
        if not algorithm_text:
            return jsonify({"error": "Failed to generate algorithm"}), 500
        return jsonify({"algorithm": algorithm_text})
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
