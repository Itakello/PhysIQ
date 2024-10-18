from pathlib import Path

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

# Color definitions
COLORS = [
    (243, 79, 70, 255),  # Red (0)
    (24, 119, 242, 255),  # Green (1)
    (107, 206, 187, 255),  # Blue (2)
    (27, 121, 242, 255),  # Azure (3)
    (75, 74, 164, 255),  # Pink (4)
    (185, 202, 210, 255),  # Gray (5)
    (0, 0, 0, 255),  # Black (6)
]

# Configuration directory
CONFIG_DIR = Path("task_jsons")
