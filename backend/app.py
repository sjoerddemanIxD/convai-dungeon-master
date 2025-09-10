import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Store conversation history
conversation_history = [
    {
        "role": "system",
        "content": (
            "You are a world-class Dungeon Master for a game of Dungeons & Dragons 5th Edition (2024 rules). "
            "Your name is ConvAI, but you will never refer to yourself. You are the narrator and all the NPCs. "
            "Your goal is to create a captivating, immersive, and collaborative storytelling experience. "
            "Describe the world in vivid detail. When the user tells you what they do, describe the outcome. "
            "Keep your responses concise and focused on the current action, ending with 'What do you do?'"
        )
    }
]

@app.route('/chat', methods=['POST'])
def chat():
    global conversation_history
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Add user message to history
    conversation_history.append({"role": "user", "content": user_message})

    try:
        chat_completion = client.chat.completions.create(
            messages=conversation_history,
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stop=None,
            stream=False,
        )
        ai_response = chat_completion.choices[0].message.content
        
        # Add AI response to history
        conversation_history.append({"role": "assistant", "content": ai_response})

        return jsonify({'response': ai_response})

    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to get response from AI"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
