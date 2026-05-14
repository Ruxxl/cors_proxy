from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv
import os

# Загружаем переменные окружения из файла .env
load_dotenv()

app = Flask(__name__, static_folder='public')

# Включаем CORS для работы с фронтендом
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
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        prompt = data.get("prompt")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Обновленное имя модели для нового SDK google-genai
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt,
        )

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
