from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv
import os
import requests

# load env
load_dotenv()

app = Flask(__name__, static_folder='public')

# =========================
# CORS — разрешаем все origins (GitHub Pages, localhost, etc.)
# =========================
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

# Дополнительно вручную добавляем заголовки для всех ответов
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# Gemini client
client = genai.Client()


# =========================
# PREFLIGHT — обрабатываем OPTIONS для всех роутов
# =========================
@app.route("/<path:path>", methods=["OPTIONS"])
@app.route("/", methods=["OPTIONS"])
def options_handler(path=""):
    return jsonify({}), 200


# =========================
# FRONTEND
# =========================
@app.route("/")
def index():
    return send_from_directory("public", "index.html")


# =========================
# GEMINI GENERATE
# =========================
@app.route("/generate", methods=["POST", "OPTIONS"])
def generate():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return jsonify({
            "result": response.text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# CONFLUENCE PROXY
# =========================
@app.route("/confluence", methods=["POST", "OPTIONS"])
def confluence():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        data = request.json

        url = data.get("url")
        email = data.get("email")
        token = data.get("token")
        page_id = data.get("pageId")

        if not all([url, email, token, page_id]):
            return jsonify({"error": "Missing required fields"}), 400

        api_url = f"{url}/wiki/rest/api/content/{page_id}?expand=body.storage"

        response = requests.get(
            api_url,
            auth=(email, token),
            headers={"Accept": "application/json"},
            timeout=20
        )

        return jsonify({
            "status": response.status_code,
            "data": response.json()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
