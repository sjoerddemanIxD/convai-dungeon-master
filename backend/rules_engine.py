# backend/rules_engine.py
import random
import re
import os
import json
import logging

class RulesEngine:
    def __init__(self, rules_directory):
        self.rules = self._load_rules(rules_directory)

    def _load_rules(self, directory):
        """Loads all .json rule files from a directory."""
        all_rules = {}
        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r') as f:
                    rules_data = json.load(f)
                    for rule in rules_data.get('rules', []):
                        event_type = rule.get('event')
                        if event_type:
                            if event_type not in all_rules:
                                all_rules[event_type] = []
                            all_rules[event_type].append(rule)
        logging.info(f"Rules engine loaded {len(all_rules)} event types.")
        return all_rules

    def _check_condition(self, character_state, condition):
        """Checks a single condition against the character's state."""
        fact_path = condition['fact'].split('.')
        
        # Traverse the character state to get the fact value
        fact_value = character_state
        for p in fact_path:
            fact_value = fact_value.get(p)
            if fact_value is None:
                return False # Path does not exist

        operator = condition['operator']
        value = condition['value']
        
        # Handle special condition values
        if value == "negative_max_hp":
            value = -character_state.get('max_hp', 0)

        # Perform the comparison
        if operator == 'lessThanOrEqual':
            return fact_value <= value
        if operator == 'greaterThanOrEqual':
            return fact_value >= value
        if operator == 'equal':
            return fact_value == value
        if operator == 'notEqual':
            return fact_value != value
            
        return False

    def process_event(self, event, character_state):
        """Processes an event, checking all relevant rules and applying effects."""
        event_type = event['type']
        triggered_effects = []

        if event_type not in self.rules:
            return triggered_effects
        
        for rule in self.rules[event_type]:
            conditions_met = True
            for condition in rule.get('conditions', []):
                if not self._check_condition(character_state, condition):
                    conditions_met = False
                    break
            
            if conditions_met:
                logging.info(f"Rule '{rule['name']}' triggered for {character_state.get('name')}.")
                # Apply all effects for this rule
                for effect in rule.get('effects', []):
                    triggered_effects.append({
                        'effect': effect,
                        'character': character_state
                    })
        
        return triggered_effects


def roll_dice(dice_notation):
    """
    Roll dice given notation like '1d20', '2d6+3', '8d6'
    Returns (result, roll_details)
    """
    try:
        # Parse dice notation (e.g., "2d6+3")
        parts = dice_notation.lower().replace('-', '+-').split('+')
        total = 0
        rolls = []
        
        for part in parts:
            part = part.strip()
            if 'd' in part:
                num, sides = part.split('d')
                num = int(num) if num else 1
                sides = int(sides)
                roll_results = [random.randint(1, sides) for _ in range(num)]
                rolls.extend(roll_results)
                total += sum(roll_results)
            elif part:
                # It's a modifier
                total += int(part)
        
        return total, rolls
    except:
        return 0, []

def check_spellcasting(character, spell):
    """
    Checks if a character can cast a given spell.
    Returns a tuple: (can_cast: bool, reason: str, details: list)
    """
    details = []
    spell_name = spell['name']
    spell_level = spell.get('level', 0)

    # Check 1: Does the character know the spell?
    spells_known = character.get('spellcasting', {}).get('spells_known', {})
    all_known_spells = spells_known.get('cantrips', []) + spells_known.get('level_1', [])
    
    if spell_name not in all_known_spells:
        details.append(f"❌ {spell_name} is not in your spell list")
        return False, f"Spell '{spell_name}' is not known.", details

    details.append(f"✓ {spell_name} is known")

    # If it's a cantrip (level 0), no further checks are needed
    if spell_level == 0:
        details.append("✓ Cantrips don't require spell slots.")
        return True, "The spell is a cantrip and can be cast.", details

    # Check 2: Is the spell prepared?
    prepared_spells = character.get('spellcasting', {}).get('prepared_spells', [])
    if spell_name not in prepared_spells:
        details.append(f"❌ {spell_name} is not prepared")
        return False, f"Spell '{spell_name}' is not prepared.", details
    
    details.append(f"✓ {spell_name} is prepared")

    # Check 3: Does the character have an available spell slot?
    slot_key = f"level_{spell_level}"
    spell_slots = character.get('spellcasting', {}).get('spell_slots', {})
    if slot_key in spell_slots:
        slots = spell_slots[slot_key]
        if slots['used'] >= slots['total']:
            details.append(f"❌ No Level {spell_level} spell slots available")
            return False, f"No available level {spell_level} spell slots.", details
        else:
            details.append(f"✓ Spell slot available: {slots['used']}/{slots['total']} Level {spell_level} slots used")
    else:
        details.append(f"❌ Character sheet does not track Level {spell_level} slots")
        return False, f"Spell slot information for level {spell_level} is not available.", details

    return True, "The character can cast the spell.", details
