from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv
import os
import requests
import base64

load_dotenv()

app = Flask(__name__, static_folder='public')

# Разрешаем ВСЕ origins явно
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "OPTIONS"])

client = genai.Client()

# Jira credentials from environment
JIRA_URL   = os.environ.get("JIRA_URL",   "https://mechtamarket.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")
JIRA_PROJECT = os.environ.get("JIRA_PROJECT", "AS")


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


# =========================
# CONFLUENCE PROXY
# =========================
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
# JIRA GET VERSIONS
# =========================
@app.route("/jira/versions", methods=["POST", "OPTIONS"])
def jira_get_versions():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы в переменных окружения"}, 500)

    try:
        data    = request.json
        project = data.get("project", JIRA_PROJECT)

        api_url = f"{JIRA_URL}/rest/api/2/project/{project}/versions"

        resp = requests.get(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json"},
            timeout=20
        )

        return cors_response({"status": resp.status_code, "data": resp.json()})

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# JIRA SEARCH ISSUES
# =========================
@app.route("/jira/issues", methods=["POST", "OPTIONS"])
def jira_search_issues():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы в переменных окружения"}, 500)

    try:
        data    = request.json
        jql     = data.get("jql")
        max_results = data.get("maxResults", 50)
        fields  = data.get("fields", "summary,status,issuetype,priority,description,subtasks")

        if not jql:
            return cors_response({"error": "jql обязателен"}, 400)

        api_url = f"{JIRA_URL}/rest/api/3/search/jql"
        params  = {"jql": jql, "maxResults": max_results, "fields": fields}

        resp = requests.get(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json"},
            params=params,
            timeout=20
        )

        return cors_response({"status": resp.status_code, "data": resp.json()})

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# JIRA CREATE SUBTASK
# =========================
@app.route("/jira/subtask", methods=["POST", "OPTIONS"])
def jira_create_subtask():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы в переменных окружения"}, 500)

    try:
        data    = request.json
        parent  = data.get("parentKey")
        summary = data.get("summary")
        project = data.get("project", JIRA_PROJECT)

        if not all([parent, summary]):
            return cors_response({"error": "parentKey и summary обязательны"}, 400)

        api_url = f"{JIRA_URL}/rest/api/2/issue"
        payload = {
            "fields": {
                "project":   {"key": project},
                "parent":    {"key": parent},
                "summary":   summary,
                "issuetype": {"name": "Подзадача"}
            }
        }

        resp = requests.post(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=payload,
            timeout=20
        )

        return cors_response({"status": resp.status_code, "data": resp.json()})

    except Exception as e:
        return cors_response({"error": str(e)}, 500)



# =========================
# JIRA UPDATE ISSUE
# =========================
@app.route("/jira/update", methods=["POST", "OPTIONS"])
def jira_update_issue():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы"}, 500)

    try:
        data      = request.json
        issue_key = data.get("issueKey")
        fields    = data.get("fields", {})

        if not issue_key:
            return cors_response({"error": "issueKey обязателен"}, 400)

        api_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}"
        payload = {"fields": fields}

        resp = requests.put(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=payload,
            timeout=20
        )

        if resp.status_code == 204:
            return cors_response({"status": 204, "ok": True})
        return cors_response({"status": resp.status_code, "data": resp.text}, resp.status_code)

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# JIRA GET ISSUE
# =========================
@app.route("/jira/issue", methods=["POST", "OPTIONS"])
def jira_get_issue():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы"}, 500)

    try:
        data      = request.json
        issue_key = data.get("issueKey")

        if not issue_key:
            return cors_response({"error": "issueKey обязателен"}, 400)

        api_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}?fields=summary,description,status,priority,issuetype,subtasks,attachment,comment"

        resp = requests.get(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json"},
            timeout=20
        )

        return cors_response({"status": resp.status_code, "data": resp.json()})

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# JIRA DELETE ISSUE
# =========================
@app.route("/jira/delete", methods=["POST", "OPTIONS"])
def jira_delete_issue():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы"}, 500)

    try:
        data      = request.json
        issue_key = data.get("issueKey")
        if not issue_key:
            return cors_response({"error": "issueKey обязателен"}, 400)

        api_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}"
        resp = requests.delete(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json"},
            timeout=20
        )
        if resp.status_code == 204:
            return cors_response({"status": 204, "ok": True})
        return cors_response({"status": resp.status_code, "data": resp.text}, resp.status_code)

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# JIRA GET TRANSITIONS
# =========================
@app.route("/jira/transitions", methods=["POST", "OPTIONS"])
def jira_get_transitions():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы"}, 500)

    try:
        data      = request.json
        issue_key = data.get("issueKey")
        if not issue_key:
            return cors_response({"error": "issueKey обязателен"}, 400)

        api_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/transitions"
        resp = requests.get(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json"},
            timeout=20
        )
        return cors_response({"status": resp.status_code, "data": resp.json()})

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# JIRA DO TRANSITION
# =========================
@app.route("/jira/transition", methods=["POST", "OPTIONS"])
def jira_do_transition():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы"}, 500)

    try:
        data          = request.json
        issue_key     = data.get("issueKey")
        transition_id = data.get("transitionId")
        if not all([issue_key, transition_id]):
            return cors_response({"error": "issueKey и transitionId обязательны"}, 400)

        api_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/transitions"
        payload = {"transition": {"id": str(transition_id)}}
        resp = requests.post(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json=payload,
            timeout=20
        )
        if resp.status_code == 204:
            return cors_response({"status": 204, "ok": True})
        return cors_response({"status": resp.status_code, "data": resp.text}, resp.status_code)

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# JIRA UPLOAD ATTACHMENT
# =========================
@app.route("/jira/attachment", methods=["POST", "OPTIONS"])
def jira_upload_attachment():
    if request.method == "OPTIONS":
        return cors_response({})

    if not JIRA_EMAIL or not JIRA_TOKEN:
        return cors_response({"error": "JIRA_EMAIL / JIRA_TOKEN не заданы в переменных окружения"}, 500)

    try:
        issue_key = request.form.get("issueKey")
        file      = request.files.get("file")

        if not all([issue_key, file]):
            return cors_response({"error": "issueKey и file обязательны"}, 400)

        api_url = f"{JIRA_URL}/rest/api/2/issue/{issue_key}/attachments"

        resp = requests.post(
            api_url,
            auth=(JIRA_EMAIL, JIRA_TOKEN),
            headers={
                "Accept": "application/json",
                "X-Atlassian-Token": "no-check"
            },
            files={"file": (file.filename, file.stream, file.content_type)},
            timeout=30
        )

        return cors_response({"status": resp.status_code, "data": resp.json()})

    except Exception as e:
        return cors_response({"error": str(e)}, 500)


# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
