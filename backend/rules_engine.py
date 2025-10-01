# backend/rules_engine.py
import random

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
