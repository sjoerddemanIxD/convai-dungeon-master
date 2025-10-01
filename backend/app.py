import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

from orchestrator import recognize_intent
from rules_engine import check_spellcasting, roll_dice

# --- Basic Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)  # Allow all origins for development
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- Global State ---
knowledge_base = {}
character_sheet = {}
active_npcs = {}  # Track NPCs in encounters: {name: {hp: current, max_hp: max}}
conversation_history = [
    {
        "role": "system",
        "content": (
            "You are a world-class Dungeon Master for a game of Dungeons & Dragons, acting as a creative storyteller. "
            "Your name is ConvAI, but you will never refer to yourself. You are the narrator and all the NPCs. "
            "You will be given the player's action, the outcome of that action according to the game rules, and a reason. "
            "Your task is to weave these elements into a compelling narrative. Describe the action, the result, and hint at the reason in your story. "
            "Keep your responses concise, about 1-3 paragraphs. Always end your response by asking the player what they do next, for example: 'What do you do?'"
        ),
    }
]
pending_action = None # Will store dict for actions needing clarification


# --- Data Loading ---
def load_knowledge_base():
    """Loads all necessary data from disk into global state."""
    global knowledge_base, character_sheet
    
    # Load Knowledge Base
    kb_path = os.path.join(os.path.dirname(__file__), 'knowledge_base')
    for filename in os.listdir(kb_path):
        if filename.endswith('.json'):
            key = os.path.splitext(filename)[0]
            filepath = os.path.join(kb_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                knowledge_base[key] = json.load(f)
    logging.info("Knowledge base loaded.")

def load_character_sheet():
    """Loads the character sheet from disk."""
    global character_sheet
    try:
        with open(os.path.join('backend', 'character.json'), 'r') as f:
            character_sheet = json.load(f)
        logging.info("Character sheet loaded.")
    except FileNotFoundError:
        logging.error("character.json not found.")
    except json.JSONDecodeError:
        logging.error("Error decoding character.json.")


@app.route('/character', methods=['GET'])
def get_character():
    return jsonify(character_sheet)


# --- KB Helper Functions ---
def _find_in_obj(obj, key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, (dict, list)): return v
            found = _find_in_obj(v, key)
            if found is not None: return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_in_obj(item, key)
            if found is not None: return found
    return None

def find_spell_rule(spell_name: str):
    spell_root = knowledge_base.get('08 spellcasting')
    if not spell_root: return None
    
    spells_dict = spell_root.get('Spells') if isinstance(spell_root, dict) else None
    if spells_dict and isinstance(spells_dict, dict):
        return spells_dict.get(spell_name)
    
    return _find_in_obj(spell_root, spell_name)

def adjudicate_and_narrate(user_message, intent_data):
    """
    Takes a complete user action (with intent) and generates a narrative.
    This function contains the core game logic.
    """
    global active_npcs, conversation_history, pending_action

    # 1. Recognize Intent (already done, just extracting variables)
    intent = intent_data.get("intent", "other")
    spell_name = intent_data.get("spell_name")
    target = intent_data.get("target")

    # 2. Adjudicate based on intent
    outcome_summary = ""
    reason = ""
    action_summary = {
        "type": "unknown",
        "success": True,
        "mechanics": []  # List of mechanical details
    }
    
    if intent == 'cast_spell' and spell_name:
        spell_rule = find_spell_rule(spell_name.title())
        action_summary["type"] = "spell"
        
        # Auto-target self if spell range is 'Self'
        if spell_rule and spell_rule.get('range') == 'Self':
            if not target:
                target = character_sheet['name']
                action_summary["mechanics"].append(f"ℹ️ Spell is self-targeted")
        
        # NEW: If target is STILL missing, and it's required, ask for it.
        if not target:
            logging.info(f"Action '{user_message}' is missing a target. Asking for clarification.")
            intent_data['original_user_message'] = user_message 
            pending_action = {'type': 'missing_target', 'intent_data': intent_data}
            question = f"What is the target of your {spell_name} spell?"
            return jsonify({
                'clarification_question': question,
                'character_name': 'DM',
                'character_portrait': ''
            })

        if not spell_rule:
            reason = f"The spell '{spell_name}' is not in the known rulebook."
            outcome_summary = f"{character_sheet['name']} tries to cast a spell that does not seem to exist."
            action_summary["success"] = False
            action_summary["mechanics"].append(f"❌ {spell_name} not found in rulebook")
        else:
            if isinstance(spell_rule, dict):
                spell_rule.setdefault('name', spell_name.title())
            
            can_act, reason, details = check_spellcasting(character_sheet, spell_rule)
            action_summary["mechanics"].extend(details)
            
            if can_act:
                outcome_summary = f"{character_sheet['name']} successfully casts {spell_name} at {target}."
                action_summary["success"] = True
                
                # Roll damage if applicable
                damage = spell_rule.get('damage')
                if damage:
                    total_damage, rolls = roll_dice(damage)
                    action_summary["mechanics"].append(f"🎲 Damage roll: {damage} = {rolls} = {total_damage} damage")
                    
                    # Apply damage to NPC
                    target_name = target.strip() if target and not target.lower().startswith("the ") else target
                    if target_name:
                        if target_name not in active_npcs:
                            active_npcs[target_name] = {"hp": 100, "max_hp": 100}
                        
                        active_npcs[target_name]["hp"] -= total_damage
                        if active_npcs[target_name]["hp"] < 0:
                            active_npcs[target_name]["hp"] = 0
                        
                        action_summary["mechanics"].append(f"💥 {target_name} takes {total_damage} damage!")
                else:
                    action_summary["mechanics"].append(f"✓ Successfully cast {spell_name} at {target}")
                    
                    # Track NPC even if no damage
                    target_name = target.strip() if target and not target.lower().startswith("the ") else target
                    if target_name and target_name not in active_npcs:
                        active_npcs[target_name] = {"hp": 100, "max_hp": 100}
            else:
                outcome_summary = f"{character_sheet['name']} fails to cast {spell_name}."
                action_summary["success"] = False

    elif any(word in user_message.lower() for word in ['attack', 'stab', 'hit', 'strike', 'slash', 'shoot', 'swing']):
        action_summary["type"] = "attack"
        action_summary["mechanics"].append(f"⚔️ Attack action: {user_message[:50]}")
        
        # Get attack bonus
        is_finesse = any(weapon in user_message.lower() for weapon in ['dagger', 'rapier', 'shortsword'])
        
        if is_finesse:
            attack_mod = character_sheet['ability_scores']['dexterity']['modifier']
            action_summary["mechanics"].append(f"📊 Using DEX modifier: +{attack_mod}")
        else:
            attack_mod = character_sheet['ability_scores']['strength']['modifier']
            action_summary["mechanics"].append(f"📊 Using STR modifier: +{attack_mod}")
        
        proficiency = character_sheet['proficiency_bonus']
        attack_bonus = attack_mod + proficiency
        
        attack_roll, rolls = roll_dice('1d20')
        total_attack = attack_roll + attack_bonus
        action_summary["mechanics"].append(f"🎲 Attack roll: 1d20({rolls[0]}) + {attack_bonus} = {total_attack}")
        
        target_ac = 15
        
        if rolls[0] == 20:
            action_summary["mechanics"].append(f"🎯 CRITICAL HIT!")
            action_summary["success"] = True
            damage_dice = '1d4' if 'dagger' in user_message.lower() else '1d8'
            damage_roll, d_rolls = roll_dice(damage_dice)
            crit_roll, c_rolls = roll_dice(damage_dice)
            total_damage = damage_roll + crit_roll + attack_mod
            action_summary["mechanics"].append(f"🎲 Damage roll: 2{damage_dice[1:]}({d_rolls[0]}, {c_rolls[0]}) + {attack_mod} = {total_damage} damage")
        elif rolls[0] == 1:
            action_summary["mechanics"].append(f"💀 CRITICAL MISS!")
            action_summary["success"] = False
            total_damage = 0
        elif total_attack >= target_ac:
            action_summary["mechanics"].append(f"✓ Hit! (vs AC {target_ac})")
            action_summary["success"] = True
            damage_dice = '1d4' if 'dagger' in user_message.lower() else '1d8'
            damage_roll, d_rolls = roll_dice(damage_dice)
            total_damage = damage_roll + attack_mod
            action_summary["mechanics"].append(f"🎲 Damage roll: {damage_dice}({d_rolls[0]}) + {attack_mod} = {total_damage} damage")
        else:
            action_summary["mechanics"].append(f"❌ Miss! (needed {target_ac})")
            action_summary["success"] = False
            total_damage = 0

        # Apply damage if hit
        if total_damage > 0:
            target_words = user_message.lower().split()
            target_name = next((target_words[i + 1].capitalize() for i, w in enumerate(target_words) if w in ['the', 'at', 'against'] and i + 1 < len(target_words)), None)
            if target_name:
                if target_name not in active_npcs:
                    active_npcs[target_name] = {"hp": 100, "max_hp": 100}
                active_npcs[target_name]["hp"] = max(0, active_npcs[target_name]["hp"] - total_damage)
                action_summary["mechanics"].append(f"💥 {target_name} takes {total_damage} damage!")
    else:
        action_summary["mechanics"].append(f"🎲 Action: {user_message[:50]}")

    # 3. Generate Narrative
    try:
        narrative_prompt = f"Player Action: '{user_message}'\nOutcome: {outcome_summary}\nReason: {reason}\n\nPlease narrate this event."
        request_history = conversation_history + [{"role": "user", "content": narrative_prompt}]
        
        chat_completion = client.chat.completions.create(
            messages=request_history,
            model="llama-3.1-8b-instant",
        )
        ai_response = (chat_completion.choices[0].message.content or "").strip()
        if not ai_response:
            ai_response = f"{outcome_summary} What do you do?"

        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        return jsonify({
            'response': ai_response,
            'character_name': character_sheet['name'],
            'character_portrait': character_sheet.get('portrait_url', ''),
            'action_summary': action_summary,
            'npcs': active_npcs
        })

    except Exception as e:
        logging.error(f"An error occurred in the chat endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred. Check the server logs for details."}), 500


@app.route('/chat', methods=['POST'])
def chat():
    global pending_action
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    if pending_action and pending_action['type'] == 'missing_target':
        logging.info(f"Received clarification for target: '{user_message}'")
        
        intent_data = pending_action['intent_data']
        original_user_message = intent_data.get('original_user_message', '')
        intent_data['target'] = user_message
        
        pending_action = None 
        
        return adjudicate_and_narrate(original_user_message, intent_data)

    try:
        logging.info(f"Processing message: {user_message}")
        intent_data = recognize_intent(client, user_message) or {}
        logging.info(f"Intent recognized successfully: {intent_data}")
        return adjudicate_and_narrate(user_message, intent_data)
    except Exception as e:
        logging.error(f"CRITICAL: An exception occurred during recognize_intent call: {e}", exc_info=True)
        return jsonify({"error": "Failed during intent recognition. Check server logs."}), 500

if __name__ == '__main__':
    load_knowledge_base()
    load_character_sheet()
    app.run(debug=True)
