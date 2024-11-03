from pathlib import Path

from ..classes.types.color import Color

# Simulation constants
SCREEN_SCALE_FACTOR = 2
RESOLUTION_SCALE_FACTOR = 4
FPS = 120
SIMULATION_STEPS_PER_FRAME = 1
TIME_SCALE = 0.25

# Physics constants
DEFAULT_GRAVITY = 1000
DEFAULT_DENSITY = 1
DEFAULT_FRICTION = 0.5
DEFAULT_RESTITUTION = 0.5
DEFAULT_ANGULAR_DAMPING = 0.0
DEFAULT_LINEAR_DAMPING = 0.0
SIMULATION_EXAMPLE_DURATION = 10

# Color definitions
COLORS = [
    Color.from_preset(Color.Preset.RED),
    Color.from_preset(Color.Preset.GREEN),
    Color.from_preset(Color.Preset.BLUE),
    Color.from_preset(Color.Preset.AZURE),
    Color.from_preset(Color.Preset.PINK),
    Color.from_preset(Color.Preset.GREY),
    Color.from_preset(Color.Preset.BLACK),
]

# Configuration directory
CONFIG_DIR = Path("task_jsons")

FONT_SIZE = 36

# Add these lines to the existing config file
PADDING_X = 20  # Horizontal padding
PADDING_Y = 60  # Vertical padding (extra space for buttons)
