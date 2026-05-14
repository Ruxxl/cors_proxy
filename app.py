from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
import os

app = Flask(__name__, static_folder='public')

CORS(app)

# Инициализируем клиент Gemini. 
# Он автоматически подтянет ключ из переменной окружения GEMINI_API_KEY
client = genai.Client()

@app.route("/")
def index():
    return send_from_directory("public", "index.html")

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.json
        prompt = data.get("prompt")

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Вызываем модель gemini-1.5-flash (оптимальная бесплатная модель)
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )

        # Текст ответа лежит напрямую в свойстве .text
        result = response.text

        return jsonify({
            "result": result
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
