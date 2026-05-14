from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import os

app = Flask(__name__, static_folder='public')

CORS(app)

client = OpenAI(
api_key=os.getenv("OPENAI_API_KEY")
)

@app.route("/")
def index():
return send_from_directory("public", "index.html")

@app.route("/generate", methods=["POST"])
def generate():
try:
data = request.json
prompt = data.get("prompt")

```
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    result = completion.choices[0].message.content

    return jsonify({
        "result": result
    })

except Exception as e:
    return jsonify({
        "error": str(e)
    }), 500
```

if **name** == "**main**":
app.run(host="0.0.0.0", port=3000)
