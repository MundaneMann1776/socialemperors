"""
Cheat Menu API endpoints for Social Empires
Performance-optimized with lazy loading
"""

from flask import Blueprint, request, jsonify, session
from sessions import session as get_save, save_session
from engine import timestamp_now
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
    except:
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
    """Add resources to player's save."""
    if 'USERID' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    USERID = session['USERID']
    save = get_save(USERID)
    
    data = request.get_json() or {}
    
    # Apply resource changes
    cash = data.get('cash', 0)
    gold = data.get('gold', 0)
    xp = data.get('xp', 0)
    stone = data.get('stone', 0)
    wood = data.get('wood', 0)
    food = data.get('food', 0)
    
    if cash:
        save["playerInfo"]["cash"] = save["playerInfo"].get("cash", 0) + cash
    if gold:
        save["maps"][0]["coins"] = save["maps"][0].get("coins", 0) + gold
    if xp:
        save["maps"][0]["xp"] = save["maps"][0].get("xp", 0) + xp
    if stone:
        save["maps"][0]["stone"] = save["maps"][0].get("stone", 0) + stone
    if wood:
        save["maps"][0]["wood"] = save["maps"][0].get("wood", 0) + wood
    if food:
        save["maps"][0]["food"] = save["maps"][0].get("food", 0) + food
    
    save_session(USERID)
    print(f"[CHEAT] Added resources for {USERID}: cash={cash}, gold={gold}, xp={xp}")
    
    return jsonify({'status': 'ok', 'reload': True})


@cheat.route('/api/cheat/spawn', methods=['POST'])
def spawn_unit():
    """Spawn unit(s) on the map."""
    if 'USERID' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    USERID = session['USERID']
    save = get_save(USERID)
    
    data = request.get_json() or {}
    unit_id = data.get('unit_id')
    quantity = min(data.get('quantity', 1), 20)  # Max 20 at once for safety
    x = data.get('x', 50)
    y = data.get('y', 50)
    
    if not unit_id:
        return jsonify({'error': 'unit_id required'}), 400
    
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
    """Set player level/XP."""
    if 'USERID' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    USERID = session['USERID']
    save = get_save(USERID)
    
    data = request.get_json() or {}
    level = data.get('level')
    
    if level:
        # Approximate XP for level (each level ~1000 XP)
        xp = level * 5000
        save["maps"][0]["xp"] = xp
        save["maps"][0]["level"] = level
        save_session(USERID)
        print(f"[CHEAT] Set level to {level} for {USERID}")
    
    return jsonify({'status': 'ok', 'reload': True})
