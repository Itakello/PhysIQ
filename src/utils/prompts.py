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

# System prompts differentiated by reasoning approach
SYSTEM_TEMPLATES = {
    "binary": """You are a physics expert analyzing simulations. Your task is to predict whether specific objects in a physics simulation will come into contact within the given timeframe. Always answer with a clear "Yes" or "No".

Simulation conditions for all tasks:
- Gravity: {DEFAULT_Y_GRAVITY} m/s² (downward)
- Objects density: {DEFAULT_DENSITY}
- Friction coefficient: {DEFAULT_FRICTION}
- Elasticity coefficient: {DEFAULT_ELASTICITY}
- Simulation duration: {SIMULATION_DURATION} seconds or until objects stop moving
- All objects remain within the visible simulation boundaries and cannot leave the simulation area
- Black and purple objects: static (fixed)
- Green, red, grey objects: dynamic (can move)
- Goal criterion: Objects must remain in contact ≥ {CONTACT_DURATION} seconds""".format(
        DEFAULT_Y_GRAVITY=DEFAULT_Y_GRAVITY,
        DEFAULT_DENSITY=DEFAULT_DENSITY,
        DEFAULT_FRICTION=DEFAULT_FRICTION,
        DEFAULT_ELASTICITY=DEFAULT_ELASTICITY,
        SIMULATION_DURATION=int((MAX_STEPS / (FPS * TIME_SCALE)) / 2),
        CONTACT_DURATION=int((GOAL_COLLISIONS_REQUIRED / (FPS * TIME_SCALE)) / 2),
    ),
    "sanity_check": """You are a physics expert analyzing simulations. Your task is to determine whether specific objects in a physics simulation are in contact. Always answer with a clear "Yes" or "No".""",
}

# Default system template
SYSTEM_TEMPLATE = SYSTEM_TEMPLATES["binary"]

# User prompt templates for different levels of instruction detail
USER_TEMPLATES = {
    # Binary prompt - includes physics parameters but still just Yes/No answer
    "binary": "Will the <TARGET_OBJ1> and <TARGET_OBJ2> come into contact for {CONTACT_DURATION} seconds?".format(
        CONTACT_DURATION=int((GOAL_COLLISIONS_REQUIRED / (FPS * TIME_SCALE)) / 2),
    ),
    # Sanity check prompt - consistent with Yes/No format
    "sanity_check": "Based on what you can see in the current state, are the <TARGET_OBJ1> and <TARGET_OBJ2> in contact?",
}
