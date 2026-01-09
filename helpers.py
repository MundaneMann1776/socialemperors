"""
Helper functions for Social Empires Server.
Provides reusable utilities to eliminate code duplication.
"""

from typing import Optional, Any, Tuple
from engine import timestamp_now
from game_constants import (
    MAX_GRAVEYARD_SLOTS,
    GRAVEYARD_EXPIRY_SECONDS,
    MAP_COORD_MIN,
    MAP_COORD_MAX
)


def add_to_graveyard(save: dict, unit_id: int, town_id: int) -> bool:
    """
    Add a unit to the graveyard with proper capacity management.
    
    Args:
        save: The player's save data
        unit_id: The ID of the unit to add
        town_id: The town/map ID
        
    Returns:
        True if unit was added, False if graveyard is disabled or error
    """
    # Initialize graveyard if needed
    if "privateState" not in save:
        return False
    
    if "graveyard" not in save["privateState"]:
        save["privateState"]["graveyard"] = []
    
    graveyard = save["privateState"]["graveyard"]
    
    # Capacity limit - remove oldest if full
    if len(graveyard) >= MAX_GRAVEYARD_SLOTS:
        removed = graveyard.pop(0)
        print(f"  -> Graveyard full, removed oldest entry (unit {removed.get('unit_id', '?')})")
    
    # Use single timestamp to avoid race condition
    ts = timestamp_now()
    
    graveyard_entry = {
        "unit_id": unit_id,
        "timestamp": ts,
        "expires_at": ts + GRAVEYARD_EXPIRY_SECONDS,
        "town_id": town_id
    }
    graveyard.append(graveyard_entry)
    print(f"  -> Added unit {unit_id} to graveyard (expires in 48 hours)")
    
    return True


def validate_coordinates(x: Any, y: Any) -> Tuple[int, int]:
    """
    Validate and clamp coordinates to valid map bounds.
    
    Args:
        x: X coordinate (may be any type)
        y: Y coordinate (may be any type)
        
    Returns:
        Tuple of (validated_x, validated_y) clamped to valid range
    """
    try:
        x_int = int(x)
        y_int = int(y)
    except (TypeError, ValueError):
        x_int = 50  # Default to center-ish
        y_int = 50
    
    x_clamped = max(MAP_COORD_MIN, min(x_int, MAP_COORD_MAX))
    y_clamped = max(MAP_COORD_MIN, min(y_int, MAP_COORD_MAX))
    
    return x_clamped, y_clamped


def validate_positive_int(value: Any, default: int = 0, max_value: Optional[int] = None) -> int:
    """
    Safely convert a value to a positive integer.
    
    Args:
        value: The value to validate
        default: Default value if conversion fails
        max_value: Optional maximum cap
        
    Returns:
        A valid positive integer
    """
    try:
        result = int(value)
        if result < 0:
            result = default
        if max_value is not None and result > max_value:
            result = max_value
        return result
    except (TypeError, ValueError):
        return default


def safe_list_get(lst: list, index: int, default: Any = None) -> Any:
    """
    Safely get an item from a list without IndexError.
    
    Args:
        lst: The list to access
        index: The index to retrieve
        default: Value to return if index is out of bounds
        
    Returns:
        The item at index, or default if out of bounds
    """
    try:
        if 0 <= index < len(lst):
            return lst[index]
        return default
    except (TypeError, AttributeError):
        return default


def safe_gift_decrement(gifts: list, item_id: int) -> bool:
    """
    Safely decrement a gift count and clean up trailing zeros.
    
    Args:
        gifts: The gifts array
        item_id: The item ID (index) to decrement
        
    Returns:
        True if decrement was successful, False if invalid
    """
    if not isinstance(gifts, list):
        return False
    
    if item_id < 0 or item_id >= len(gifts):
        return False
    
    if gifts[item_id] <= 0:
        return False
    
    gifts[item_id] -= 1
    
    # Clean up trailing zeros
    while gifts and gifts[-1] == 0:
        gifts.pop()
    
    return True


def clean_quest_units(save: dict) -> int:
    """
    Clean orphaned quest_units from a save.
    
    Args:
        save: The player's save data
        
    Returns:
        Number of orphaned entries removed
    """
    if "privateState" not in save:
        return 0
    
    quest_units = save["privateState"].get("quest_units", [])
    if quest_units:
        count = len(quest_units)
        save["privateState"]["quest_units"] = []
        print(f"   - Cleaned {count} orphaned quest units")
        return count
    
    return 0
