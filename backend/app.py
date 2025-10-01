import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

from orchestrator import recognize_intent
from rules_engine import check_spellcasting, roll_dice, RulesEngine
from world_model import WorldModel

# --- Basic Setup ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)  # Allow all origins for development
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# --- Global State ---
knowledge_base = {}
character_sheet = {}
world_model = None # Will be initialized on startup
rules_engine = None # Will be initialized on startup
conversation_history = [
    {
        "role": "system",
        "content": (
            "You are a world-class Dungeon Master for a game of Dungeons & Dragons, acting as a creative storyteller. "
            "Your name is ConvAI, but you will never refer to yourself. You are the narrator and all the NPCs. "
            "You will be given context about the current WORLD STATE in JSON format. Use this to ensure your descriptions are consistent. "
            "You will also be given the PLAYER'S ACTION and its precise MECHANICAL OUTCOME. "
            "Your first task is to weave the player's action and its outcome into a compelling narrative (1-3 paragraphs). "
            "After describing the player's action, determine if any NPCs should react or take their own actions. If so, narrate their actions as well. "
            "Your second task is to determine if these events cause any *non-mechanical* changes to the world state. "
            "For example, a character's emotional status might change ('enraged', 'frightened'), or an object might be altered ('dented', 'glowing'). "
            "CRITICAL: DO NOT modify mechanical stats like HP, as those have already been calculated. "
            "You MUST return a valid JSON object containing two keys: "
            "1. 'narration': A string containing your full story. End it by asking the player what they do next (e.g., 'What do you do?'). "
            "2. 'world_state_update': A JSON object detailing ONLY non-mechanical changes to the world state. If nothing changes, provide an empty object {}."
        ),
    }
]
pending_action = None # Will store dict for actions needing clarification


# --- Data Loading ---
def load_world_model():
    """Loads the initial world state and initializes the WorldModel."""
    global world_model, character_sheet
    try:
        filepath = os.path.join(os.path.dirname(__file__), 'initial_world_state.json')
        with open(filepath, 'r', encoding='utf-8') as f:
            initial_state = json.load(f)

        # Add the player character to the initial state from character_sheet
        if character_sheet:
            player_name = character_sheet.get("name")
            if player_name:
                # Copy the entire character sheet as the base for the player's state
                player_state = character_sheet.copy()
                player_state["is_player"] = True # Flag to identify the player
                player_state["status"] = "active"
                
                # Ensure HP is nested correctly for consistency
                player_state["hp"] = character_sheet.get("combat", {}).get("hit_points", {}).get("current", 10)
                player_state["max_hp"] = character_sheet.get("combat", {}).get("hit_points", {}).get("max", 10)

                initial_state["characters"][player_name] = player_state
                logging.info(f"Player '{player_name}' added to the world model.")

        world_model = WorldModel(initial_state)
        logging.info("World model initialized.")
    except FileNotFoundError:
        logging.error("initial_world_state.json not found. Using default state.")
        world_model = WorldModel()
    except json.JSONDecodeError:
        logging.error("Error decoding initial_world_state.json. Using default state.")
        world_model = WorldModel()

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
    # Also include the character's current HP from the world model
    player_name = character_sheet.get("name")
    player_state = world_model.state.get("characters", {}).get(player_name, {})
    
    # Return the dynamic player state from the world model
    return jsonify(player_state)


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
    global conversation_history, pending_action, world_model

    player_name = character_sheet.get("name")
    player_state = world_model.state.get("characters", {}).get(player_name, {})
    if not player_state:
        return jsonify({"error": "Player character not found in world state."}), 500

    # 1. Recognize Intent (already done, just extracting variables)
    intent = intent_data.get("intent", "other")
    spell_name = intent_data.get("spell_name")
    target = intent_data.get("target")

    # Overwrite target if it's a self-reference
    self_keywords = ['myself', 'me', 'my self', player_name.lower(), 'yourself', 'self']
    if target and target.lower() in self_keywords:
        target = player_name
        logging.info(f"Remapped self-targeting keyword to '{player_name}'")

    # Check for self-targeting keywords if target is initially missed
    if not target:
        if any(keyword in user_message.lower() for keyword in self_keywords):
            target = player_name
            logging.info(f"Detected self-targeting, target set to: {target}")

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
                target = player_name
                action_summary["mechanics"].append(f"ℹ️ Spell is self-targeted")
        
        # If target is STILL missing, and it's required, ask for it.
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
            outcome_summary = f"{player_name} tries to cast a spell that does not seem to exist."
            action_summary["success"] = False
            action_summary["mechanics"].append(f"❌ {spell_name} not found in rulebook")
        else:
            if isinstance(spell_rule, dict):
                spell_rule.setdefault('name', spell_name.title())
    
            can_act, reason, details = check_spellcasting(player_state, spell_rule)
            action_summary["mechanics"].extend(details)
            
            if can_act:
                outcome_summary = f"{player_name} successfully casts {spell_name} at {target}."
                action_summary["success"] = True
                
                # Roll damage if applicable
                damage = spell_rule.get('damage')
                if damage:
                    total_damage, rolls = roll_dice(damage)
                    action_summary["mechanics"].append(f"🎲 Damage roll: {damage} = {rolls} = {total_damage} damage")
                    
                    # Apply damage to character in world model
                    target_name = target.title().strip().replace("The ", "")
                    
                    characters = world_model.state.get("characters", {})
                    if target_name not in characters:
                        # Create a generic NPC if the target doesn't exist
                        characters[target_name] = {
                            "name": target_name,
                            "hp": 30, 
                            "max_hp": 30, 
                            "status": "active",
                            "is_player": False
                        }
                    
                    # Apply damage
                    char_to_update = characters[target_name]
                    new_hp = char_to_update.get("hp", 30) - total_damage
                    char_to_update["hp"] = max(0, new_hp)
                    
                    # Also update the nested combat stats if they exist (for player)
                    if "combat" in char_to_update and "hit_points" in char_to_update["combat"]:
                        char_to_update["combat"]["hit_points"]["current"] = char_to_update["hp"]

                    world_model.update_state({"characters": characters})
                    action_summary["mechanics"].append(f"💥 {target_name} takes {total_damage} damage!")

                    # --- Fire Event for Rules Engine ---
                    event = {"type": "CHARACTER_HP_CHANGED"}
                    effects = rules_engine.process_event(event, char_to_update)
                    for item in effects:
                        effect = item['effect']
                        character = item['character']
                        if effect['action'] == 'update_character_state':
                            world_model.update_state({'characters': {character['name']: effect['updates']}})
                            logging.info(f"Applied effect: {effect['updates']} to {character['name']}")
                        if effect['action'] == 'add_log_message':
                            message = effect['message'].format(character=character)
                            action_summary["mechanics"].append(f"룰 {message}")
                else:
                    action_summary["mechanics"].append(f"✓ Successfully cast {spell_name} at {target}")
                    
                    # Ensure target character exists in world model
                    target_name = target.title().strip().replace("The ", "")
                    characters = world_model.state.get("characters", {})
                    if target_name and target_name not in characters:
                        characters[target_name] = {"hp": 30, "max_hp": 30, "status": "active"}
                        world_model.update_state({"characters": characters})
            else:
                outcome_summary = f"{player_name} fails to cast {spell_name}."
                action_summary["success"] = False

    elif any(word in user_message.lower() for word in ['attack', 'stab', 'hit', 'strike', 'slash', 'shoot', 'swing']):
        action_summary["type"] = "attack"
        action_summary["mechanics"].append(f"⚔️ Attack action: {user_message[:50]}")
        
        # Establish the target for the attack and get their state
        target_name = target if target else player_name # Default to attacking self if not specified
        characters = world_model.state.get("characters", {})
        target_state = characters.get(target_name)

        # Get attack bonus
        is_finesse = any(weapon in user_message.lower() for weapon in ['dagger', 'rapier', 'shortsword'])
        
        if is_finesse:
            attack_mod = player_state['ability_scores']['dexterity']['modifier']
            action_summary["mechanics"].append(f"📊 Using DEX modifier: +{attack_mod}")
        else:
            attack_mod = player_state['ability_scores']['strength']['modifier']
            action_summary["mechanics"].append(f"📊 Using STR modifier: +{attack_mod}")
        
        proficiency = player_state['proficiency_bonus']
        attack_bonus = attack_mod + proficiency
        
        attack_roll, rolls = roll_dice('1d20')
        total_attack = attack_roll + attack_bonus
        action_summary["mechanics"].append(f"🎲 Attack roll: 1d20({rolls[0]}) + {attack_bonus} = {total_attack}")
        
        # Get target AC
        if target_state:
            target_ac = target_state.get('combat', {}).get('armor_class', 10)
        else:
            target_ac = 15 # Default AC for creatures not yet in the world model
        
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
        
        # Create a clear outcome summary for the AI
        outcome_summary = "The attack hits!" if action_summary["success"] else "The attack misses."
        if total_damage > 0:
            outcome_summary += f" {target_name} takes {total_damage} damage."

        # Apply damage if hit
        if total_damage > 0:
            # target_name is already correctly defined above
            if target_name:
                characters = world_model.state.get("characters", {})
                if target_name not in characters:
                    # This should not happen for self-attacks, but as a fallback
                    characters[target_name] = {
                        "name": target_name,
                        "hp": 30, 
                        "max_hp": 30, 
                        "status": "active",
                        "is_player": False
                    }
                
                char_to_update = characters[target_name]
                new_hp = char_to_update.get("hp", 30) - total_damage
                char_to_update["hp"] = max(0, new_hp)

                # Also update the nested combat stats if they exist (for player)
                if "combat" in char_to_update and "hit_points" in char_to_update["combat"]:
                    char_to_update["combat"]["hit_points"]["current"] = char_to_update["hp"]

                world_model.update_state({"characters": characters})
                action_summary["mechanics"].append(f"💥 {target_name} takes {total_damage} damage!")
                
                # --- Fire Event for Rules Engine ---
                event = {"type": "CHARACTER_HP_CHANGED"}
                effects = rules_engine.process_event(event, char_to_update)
                for item in effects:
                    effect = item['effect']
                    character = item['character']
                    if effect['action'] == 'update_character_state':
                        world_model.update_state({'characters': {character['name']: effect['updates']}})
                        logging.info(f"Applied effect: {effect['updates']} to {character['name']}")
                    if effect['action'] == 'add_log_message':
                        message = effect['message'].format(character=character)
                        action_summary["mechanics"].append(f"룰 {message}")
    else:
        action_summary["mechanics"].append(f"🎲 Action: {user_message[:50]}")
        outcome_summary = "An action is attempted."

    # 3. Generate Narrative
    try:
        world_context = world_model.get_context_for_prompt()
        mechanical_summary = "\n".join(action_summary["mechanics"])
        
        narrative_prompt = (
            f"WORLD STATE: {json.dumps(world_context)}\n\n"
            f"PLAYER ACTION: '{user_message}'\n"
            f"MECHANICAL OUTCOME: {outcome_summary}\n"
            f"MECHANICAL DETAILS:\n{mechanical_summary}\n\n"
            "Based on all of this, provide the JSON response with 'narration' and a 'world_state_update' for any *non-mechanical changes*."
        )
        
        # We only need the system prompt and the current request, not the whole history
        request_messages = [
            conversation_history[0], # System prompt
            {"role": "user", "content": narrative_prompt}
        ]
        
        chat_completion = client.chat.completions.create(
            messages=request_messages,
            model="llama-3.1-8b-instant", # Reverting to the smaller, more stable model
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        
        response_text = (chat_completion.choices[0].message.content or "{}").strip()
        response_data = json.loads(response_text)
        
        ai_response = response_data.get("narration", f"{outcome_summary} What do you do?")
        world_updates = response_data.get("world_state_update", {})

        # Update our world model with the changes from the AI
        if world_updates:
            world_model.update_state(world_updates)
            logging.info(f"World state updated with: {world_updates}")

        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "assistant", "content": ai_response})
        
        return jsonify({
            'response': ai_response,
            'character_name': player_name,
            'character_portrait': player_state.get('portrait_url', ''),
            'action_summary': action_summary,
            'npcs': world_model.state.get("characters", {})
        })

    except json.JSONDecodeError as json_err:
        logging.error(f"Failed to decode JSON from AI response: {response_text}. Error: {json_err}")
        return jsonify({"error": "Failed to parse AI response. Check logs."}), 500
    except Exception as e:
        logging.error(f"CRITICAL: An exception occurred during recognize_intent call: {e}", exc_info=True)
        return jsonify({"error": "Failed during intent recognition. Check server logs."}), 500


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
    load_world_model()
    # Initialize the rules engine
    rules_directory = os.path.join(os.path.dirname(__file__), 'rules')
    rules_engine = RulesEngine(rules_directory)
    app.run(debug=True)
