"""
Game constants for Social Empires Server.
Centralizes magic numbers for maintainability.
"""

# Graveyard System
MAX_GRAVEYARD_SLOTS = 20
GRAVEYARD_EXPIRY_SECONDS = 48 * 3600  # 48 hours

# Cheat Menu Limits
MAX_SPAWN_QUANTITY = 20
MAX_CHEAT_RESOURCE = 10_000_000  # Cap for single resource addition
MAX_CHEAT_LEVEL = 500  # Reasonable max level

# Map Coordinates (approximate; real map is isometric)
MAP_COORD_MIN = 0
MAP_COORD_MAX = 100

# Economy
XP_PER_LEVEL = 5000  # Approximate XP per level for cheat level-setting

# Rate Limiting
BOOST_COOLDOWN_SECONDS = 60  # Minimum seconds between /boost calls per user

# Resurrection
MIN_RESURRECTION_COST = 5  # Minimum cash cost to resurrect
RESURRECTION_COST_DIVISOR = 100  # Unit life / this = cost

# Backup System
SAVE_COUNT_BEFORE_BACKUP = 10  # Create backup every N saves
