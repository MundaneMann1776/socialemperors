"""
Cheat Menu API endpoints for Social Empires
Performance-optimized with lazy loading and input validation
"""

from flask import Blueprint, request, jsonify, session
from sessions import session as get_save, save_session
from engine import timestamp_now
from helpers import validate_positive_int, validate_coordinates
from game_constants import (
    MAX_SPAWN_QUANTITY,
    MAX_CHEAT_RESOURCE,
    MAX_CHEAT_LEVEL,
    XP_PER_LEVEL
)
import json

cheat = Blueprint('cheat', __name__)

# Cache for unit data (lazy loaded)
_unit_cache = None


def get_unit_categories():
    """Lazy load and categorize units from game config."""
    global _unit_cache
    if _unit_cache is not None:
        return _unit_cache
    
    try:
        with open('config/game_config_20120826.json', 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        print(f"[CHEAT] Failed to load game config: {e}")
        return {}
    
    items = config.get('items', [])
    categories = {
        'dragons': [],
        'draggies': [],
        'gods': [],
        'infantry': [],
        'ranged': [],
        'siege': [],
        'special': []
    }
    
    for item in items:
        if item.get('type') != 'u':
            continue
        
        unit_id = int(item.get('id', 0))
        name = item.get('name', 'Unknown')
        groups = item.get('groups', '').lower()
        name_lower = name.lower()
        
        unit_data = {
            'id': unit_id,
            'name': name,
            'attack': int(item.get('attack', 0)),
            'life': int(item.get('life', 0)),
            'groups': groups
        }
        
        # Categorize
        if 'dragon' in name_lower or 'bahamut' in name_lower or 'wyrm' in name_lower:
            categories['dragons'].append(unit_data)
        elif 'draggy' in groups:
            categories['draggies'].append(unit_data)
        elif 'god' in groups:
            categories['gods'].append(unit_data)
        elif 'siege' in groups or 'catapult' in name_lower or 'cannon' in name_lower:
            categories['siege'].append(unit_data)
        elif 'ranged' in groups or 'archer' in name_lower or 'crossbow' in name_lower:
            categories['ranged'].append(unit_data)
        elif 'melee' in groups or 'sword' in name_lower or 'knight' in name_lower:
            categories['infantry'].append(unit_data)
        else:
            categories['special'].append(unit_data)
    
    # Sort each category by attack (strongest first)
    for cat in categories:
        categories[cat].sort(key=lambda x: -x['attack'])
    
    _unit_cache = categories
    return categories


@cheat.route('/api/units', methods=['GET'])
def api_get_units():
    """Return categorized unit list for cheat menu."""
    categories = get_unit_categories()
    
    # Return summary with counts for performance
    summary = {}
    for cat, units in categories.items():
        summary[cat] = {
            'count': len(units),
            'units': units[:50]  # Limit to top 50 per category
        }
    
    return jsonify(summary)


@cheat.route('/api/units/<category>', methods=['GET'])
def api_get_category(category):
    """Get all units in a specific category."""
    categories = get_unit_categories()
    if category not in categories:
        return jsonify({'error': 'Unknown category'}), 404
    
    return jsonify(categories[category])


@cheat.route('/api/cheat/resources', methods=['POST'])
def add_resources():
    """Add resources to player's save with validation."""
    if 'USERID' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    USERID = session['USERID']
    save = get_save(USERID)
    
    if save is None:
        return jsonify({'error': 'Save not found'}), 404
    
    data = request.get_json() or {}
    
    # Validate and clamp all resource values
    # Only accept positive integers, capped at MAX_CHEAT_RESOURCE
    cash = validate_positive_int(data.get('cash', 0), 0, MAX_CHEAT_RESOURCE)
    gold = validate_positive_int(data.get('gold', 0), 0, MAX_CHEAT_RESOURCE)
    xp = validate_positive_int(data.get('xp', 0), 0, MAX_CHEAT_RESOURCE)
    stone = validate_positive_int(data.get('stone', 0), 0, MAX_CHEAT_RESOURCE)
    wood = validate_positive_int(data.get('wood', 0), 0, MAX_CHEAT_RESOURCE)
    food = validate_positive_int(data.get('food', 0), 0, MAX_CHEAT_RESOURCE)
    
    # Apply resource changes (only if positive after validation)
    if cash > 0:
        save["playerInfo"]["cash"] = save["playerInfo"].get("cash", 0) + cash
    if gold > 0:
        save["maps"][0]["coins"] = save["maps"][0].get("coins", 0) + gold
    if xp > 0:
        save["maps"][0]["xp"] = save["maps"][0].get("xp", 0) + xp
    if stone > 0:
        save["maps"][0]["stone"] = save["maps"][0].get("stone", 0) + stone
    if wood > 0:
        save["maps"][0]["wood"] = save["maps"][0].get("wood", 0) + wood
    if food > 0:
        save["maps"][0]["food"] = save["maps"][0].get("food", 0) + food
    
    save_session(USERID)
    print(f"[CHEAT] Added resources for {USERID}: cash={cash}, gold={gold}, xp={xp}")
    
    return jsonify({'status': 'ok', 'reload': True})


@cheat.route('/api/cheat/spawn', methods=['POST'])
def spawn_unit():
    """Spawn unit(s) on the map with validation."""
    if 'USERID' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    USERID = session['USERID']
    save = get_save(USERID)
    
    if save is None:
        return jsonify({'error': 'Save not found'}), 404
    
    data = request.get_json() or {}
    
    # Validate unit_id
    unit_id = validate_positive_int(data.get('unit_id'), default=0)
    if unit_id <= 0:
        return jsonify({'error': 'unit_id required and must be positive'}), 400
    
    # Validate quantity (1 to MAX_SPAWN_QUANTITY)
    quantity = validate_positive_int(data.get('quantity', 1), default=1, max_value=MAX_SPAWN_QUANTITY)
    if quantity < 1:
        quantity = 1
    
    # Validate coordinates
    x, y = validate_coordinates(data.get('x', 50), data.get('y', 50))
    
    ts = timestamp_now()
    
    # Add units with slight offset so they don't stack
    for i in range(quantity):
        offset_x = (i % 5) * 2
        offset_y = (i // 5) * 2
        unit_entry = [unit_id, x + offset_x, y + offset_y, 0, ts, 0]
        save["maps"][0]["items"].append(unit_entry)
    
    save_session(USERID)
    print(f"[CHEAT] Spawned {quantity}x unit {unit_id} at ({x},{y}) for {USERID}")
    
    return jsonify({'status': 'ok', 'reload': True, 'spawned': quantity})


@cheat.route('/api/cheat/level', methods=['POST'])
def set_level():
    """Set player level/XP with validation."""
    if 'USERID' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    USERID = session['USERID']
    save = get_save(USERID)
    
    if save is None:
        return jsonify({'error': 'Save not found'}), 404
    
    data = request.get_json() or {}
    
    # Validate level (must be >= 1, capped at MAX_CHEAT_LEVEL)
    level = validate_positive_int(data.get('level'), default=0, max_value=MAX_CHEAT_LEVEL)
    
    if level < 1:
        return jsonify({'error': 'Level must be at least 1'}), 400
    
    # Calculate XP for level using constant
    xp = level * XP_PER_LEVEL
    save["maps"][0]["xp"] = xp
    save["maps"][0]["level"] = level
    save_session(USERID)
    print(f"[CHEAT] Set level to {level} for {USERID}")
    
    return jsonify({'status': 'ok', 'reload': True})
