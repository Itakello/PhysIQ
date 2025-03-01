from src.utils.const import (
    DEFAULT_DENSITY,
    DEFAULT_ELASTICITY,
    DEFAULT_FRICTION,
    DEFAULT_Y_GRAVITY,
    FPS,
    GOAL_COLLISIONS_REQUIRED,
    MAX_STEPS,
    TIME_SCALE,
)

SIMULATION_CONDITIONS = """Simulation conditions for all tasks:
- Gravity: {DEFAULT_Y_GRAVITY} m/s² (downward)
- Objects density: {DEFAULT_DENSITY}
- Friction coefficient: {DEFAULT_FRICTION}
- Elasticity coefficient: {DEFAULT_ELASTICITY}
- Simulation duration: {SIMULATION_DURATION} seconds or until objects stop moving
- Black and purple objects: static (fixed)
- Green, red, grey objects: dynamic (can move)
- Goal criterion: Objects must remain in contact ≥ {CONTACT_DURATION} seconds
- Objects cannot leave the visible simulation boundaries""".format(
    DEFAULT_Y_GRAVITY=DEFAULT_Y_GRAVITY,
    DEFAULT_DENSITY=DEFAULT_DENSITY,
    DEFAULT_FRICTION=DEFAULT_FRICTION,
    DEFAULT_ELASTICITY=DEFAULT_ELASTICITY,
    SIMULATION_DURATION=int((MAX_STEPS / (FPS * TIME_SCALE)) / 2),
    CONTACT_DURATION=int((GOAL_COLLISIONS_REQUIRED / (FPS * TIME_SCALE)) / 2),
)

# System prompts differentiated by reasoning approach
SYSTEM_TEMPLATES = {
    "sanity_check": """You are a physics expert analyzing object interactions in physics simulations.
    
**Task**: You will receive an image depicting the current state of a simulation. Determine if the specified objects are currently in contact.

**Response format**: Answer clearly and exclusively with "Yes" or "No".""",
    "binary": """You are a physics expert analyzing object interactions in physics simulations.

{SIMULATION_CONDITIONS}

**Task:** Given an initial image of a physics simulation, predict whether the specified objects will come into contact for the required duration.

**Response format:** Answer clearly and exclusively with "Yes" or "No".""".format(
        SIMULATION_CONDITIONS=SIMULATION_CONDITIONS,
    ),
    "ranking": """You are a physics expert analyzing physics simulations.

{SIMULATION_CONDITIONS}

**Task:** You will receive 4 images, each depicting a different proposal for solving the puzzle. Rank the proposals clearly based on their likelihood of satisfying the goal, from highest likelihood (first) to lowest likelihood (last).

**Response format:** List proposal indices in order from highest to lowest likelihood (e.g., `[3, 1, 4, 2]`).
""".format(
        SIMULATION_CONDITIONS=SIMULATION_CONDITIONS,
    ),
}

# User prompt templates for different levels of instruction detail
USER_TEMPLATES = {
    "sanity_check": "Based on the current state, are the <TARGET_OBJ1> and <TARGET_OBJ2> in contact?",
    "binary": "Will the <TARGET_OBJ1> and <TARGET_OBJ2> come into contact for {CONTACT_DURATION} seconds?".format(
        CONTACT_DURATION=int((GOAL_COLLISIONS_REQUIRED / (FPS * TIME_SCALE)) / 2),
    ),
    "ranking": """Will the <TARGET_OBJ1> and <TARGET_OBJ2> come into contact for {CONTACT_DURATION} seconds?

Rank the following proposals by their likelihood of success:
""".format(
        CONTACT_DURATION=int((GOAL_COLLISIONS_REQUIRED / (FPS * TIME_SCALE)) / 2),
    ),
}
