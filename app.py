from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = Flask(__name__, static_folder='public')


CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "OPTIONS"])

client = genai.Client()


def cors_response(data, status=200):
    resp = make_response(jsonify(data), status)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


@app.after_request
def inject_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/")
def index():
    return send_from_directory("public", "index.html")

@app.route("/generate", methods=["POST", "OPTIONS"])
def generate():
    if request.method == "OPTIONS":
        return cors_response({})

    try:
        data = request.json
        if not data:
            return cors_response({"error": "No JSON data provided"}, 400)

        prompt = data.get("prompt")
        if not prompt:
            return cors_response({"error": "Prompt is required"}, 400)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return cors_response({"result": response.text})

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


@app.route("/confluence", methods=["POST", "OPTIONS"])
def confluence():
    if request.method == "OPTIONS":
        return cors_response({})

    try:
        data = request.json
        url = data.get("url")
        email = data.get("email")
        token = data.get("token")
        page_id = data.get("pageId")

        if not all([url, email, token, page_id]):
            return cors_response({"error": "Missing required fields"}, 400)

        api_url = f"{url}/wiki/rest/api/content/{page_id}?expand=body.storage"

        response = requests.get(
            api_url,
            auth=(email, token),
            headers={"Accept": "application/json"},
            timeout=20
        )

        return cors_response({"status": response.status_code, "data": response.json()})

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
