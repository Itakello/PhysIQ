from src.utils.const import (
    DEFAULT_DENSITY,
    DEFAULT_ELASTICITY,
    DEFAULT_FRICTION,
    DEFAULT_Y_GRAVITY,
    PROMPT_DIRECT,
)

# System prompts differentiated by reasoning approach
SYSTEM_TEMPLATES = {
    "direct": """You are a physics expert analyzing simulations.
Your task is to predict whether specific objects in a physics simulation will come into contact within the given timeframe.
Always answer with a clear "Yes" or "No".""",
    "detailed": """You are a physics expert analyzing simulations.
Your task is to predict whether specific objects in a physics simulation will come into contact within the given timeframe.
Always answer with a clear "Yes" or "No".""",
    "cot": """You are a physics expert analyzing simulations.
Your task is to predict whether specific objects in a physics simulation will come into contact within the given timeframe.
First provide your step-by-step reasoning, then end with a clear "Yes" or "No" answer.""",
    "sanity_check": """You are a physics expert analyzing simulations.
Your task is to determine whether specific objects in a physics simulation have already come into contact.
Always answer with a clear "Yes" or "No".""",
}

# Default system template
SYSTEM_TEMPLATE = SYSTEM_TEMPLATES["direct"]

# User prompt templates for different levels of instruction detail
USER_TEMPLATES = {
    # Direct prompt - essential information only
    "direct": {
        "description": """In this physics simulation task:
- Standard gravity is applied (downward force)
- The simulation will run for 50 seconds or until objects stop moving
- Black and purple objects are static (fixed in place)
- Green, red and grey objects are dynamic (can move)
- The goal is satisfied if 2 objects remain in contact for at least 6 seconds""",
        "question": """I need to know if the <TARGET_OBJ1> and <TARGET_OBJ2> will come into contact within 50 seconds.

Will these objects come into contact within the time limit?
Answer with only "Yes" or "No".""",
    },
    # Detailed prompt - includes physics parameters but still just Yes/No answer
    "detailed": {
        "description": """In this physics simulation task:
- Gravity: {DEFAULT_Y_GRAVITY} m/s²
- Object density: {DEFAULT_DENSITY}
- Friction coefficient: {DEFAULT_FRICTION}
- Elasticity coefficient: {DEFAULT_ELASTICITY}
- The simulation will run for 50 seconds or until objects stop moving
- Black and purple objects are static (fixed in place)
- Green, red and grey objects are dynamic (can move)
- The goal is satisfied if 2 objects remain in contact for at least 6 seconds""".format(
            DEFAULT_Y_GRAVITY=DEFAULT_Y_GRAVITY,
            DEFAULT_DENSITY=DEFAULT_DENSITY,
            DEFAULT_FRICTION=DEFAULT_FRICTION,
            DEFAULT_ELASTICITY=DEFAULT_ELASTICITY,
        ),
        "question": """I need to know if the <TARGET_OBJ1> and <TARGET_OBJ2> will come into contact within 50 seconds.

Will these objects come into contact within the time limit?
Answer with only "Yes" or "No".""",
    },
    # Chain-of-Thought prompt - guides analytical reasoning with explicit CoT before answer
    "cot": {
        "description": """In this physics simulation task:
- Gravity: {DEFAULT_Y_GRAVITY} m/s²
- Object density: {DEFAULT_DENSITY}
- Friction coefficient: {DEFAULT_FRICTION}
- Elasticity coefficient: {DEFAULT_ELASTICITY}
- The simulation will run for 50 seconds or until objects stop moving
- Black and purple objects are static (fixed in place)
- Green, red and grey objects are dynamic (can move)
- The goal is satisfied if 2 objects remain in contact for at least 6 seconds""".format(
            DEFAULT_Y_GRAVITY=DEFAULT_Y_GRAVITY,
            DEFAULT_DENSITY=DEFAULT_DENSITY,
            DEFAULT_FRICTION=DEFAULT_FRICTION,
            DEFAULT_ELASTICITY=DEFAULT_ELASTICITY,
        ),
        "question": """I need to know if the <TARGET_OBJ1> and <TARGET_OBJ2> will come into contact within 50 seconds.

Think through this step by step:
1. Identify the initial positions and properties of key objects
2. Predict how gravity and other forces will affect their movement
3. Determine if the <TARGET_OBJ1> and <TARGET_OBJ2> will make contact within the time limit

First provide your step-by-step reasoning, then end with your final answer as "Yes" or "No".""",
    },
    # Sanity check prompt - consistent with Yes/No format
    "sanity_check": {
        "description": """The image shows a physics simulation:
- Black and purple objects are static (fixed in place)
- Green, red and grey objects are dynamic (can move)""",
        "question": """Based on what you can see in the current state, have the <TARGET_OBJ1> and <TARGET_OBJ2> already made contact?
Answer with only "Yes" or "No".""",
    },
}

# For backward compatibility, create flat templates from the structured ones
FLAT_USER_TEMPLATES = {
    prompt_type: f"{template['description']}\n\n{template['question']}"
    for prompt_type, template in USER_TEMPLATES.items()
}

# Default template to use if not specified
USER_TEMPLATE = FLAT_USER_TEMPLATES[PROMPT_DIRECT]
