# backend/orchestrator.py
import json
import logging
from groq import Groq

def recognize_intent(client: Groq, user_message: str):
    """
    Uses a fast LLM call to determine the player's intent.
    """
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert D&D analyst. Your task is to determine the player's intent from their message. 
                                Classify the intent into one of the following categories: 'cast_spell', 'attack', 'skill_check', 'movement', 'interaction', 'inventory', or 'other'.
                                
                                CRITICAL: If the intent is 'cast_spell', extract:
                                - spell_name: The exact name of the spell
                                - target: Who or what they're casting it at (or null if not specified)
                                
                                If the intent is 'attack', extract:
                                - weapon: The weapon being used
                                - target: Who or what they're attacking (or null if not specified)
                                
                                Respond with ONLY a JSON object in this exact format:
                                - For spells: {"intent": "cast_spell", "spell_name": "Fireball", "target": "the goblins" or null}
                                - For attacks: {"intent": "attack", "weapon": "longsword", "target": "the orc" or null}
                                - For other intents: {"intent": "category"}
                                
                                Examples:
                                - "I cast Fireball at the goblins" -> {"intent": "cast_spell", "spell_name": "Fireball", "target": "the goblins"}
                                - "I cast Fireball" -> {"intent": "cast_spell", "spell_name": "Fireball", "target": null}"""
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        response_text = chat_completion.choices[0].message.content
        return json.loads(response_text)
    except Exception as e:
        logging.error(f"Error in intent recognition: {e}", exc_info=True)
        return {"intent": "other", "target": None}
