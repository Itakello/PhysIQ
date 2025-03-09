from src.utils.const import (
    DEFAULT_DENSITY,
    DEFAULT_ELASTICITY,
    DEFAULT_FRICTION,
    DEFAULT_Y_GRAVITY,
    FPS,
    GOAL_COLLISIONS_REQUIRED,
    MAX_RADIUS,
    MAX_STEPS,
    MIN_RADIUS,
    SCENE_DIMENSIONS,
    TIME_SCALE,
)

# Interactive evaluation status codes
INTERACTIVE_STATUSES = {
    "OUTSIDE_BOUNDARIES",
    "OVERLAPPING",
    "GOAL_NOT_REACHED",
    "GOAL_REACHED",
    "JSON_INCORRECT_FORMAT",
}

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

CONTACT_DURATION = int((GOAL_COLLISIONS_REQUIRED / (FPS * TIME_SCALE)) / 2)

# System prompts differentiated by reasoning approach
SYSTEM_TEMPLATES = {
    "sanity_check": """You are a physics expert analyzing object interactions in physics simulations.
    
**Task**: You will receive an image depicting the current state of a simulation. Determine if the specified objects are currently in contact.

**Response format**: Answer clearly and exclusively with "Yes" or "No".""",
    "binary": f"""You are a physics expert analyzing object interactions in physics simulations.

{SIMULATION_CONDITIONS}

**Task:** Given an initial image of a physics simulation, predict whether the specified objects will come into contact for the required duration.

**Response format:** Answer clearly and exclusively with "Yes" or "No".""",
    "ranking": f"""You are a physics expert analyzing physics simulations.

{SIMULATION_CONDITIONS}

**Task:** You will receive 4 images, each depicting a different proposal for solving the puzzle. Rank the proposals clearly based on their likelihood of satisfying the goal, from highest likelihood (first) to lowest likelihood (last).

**Response format:** List ONLY the proposal indices in order from highest to lowest likelihood (e.g., `[3, 1, 4, 2]`). Do NOT include explanations, reasoning, or any other additional text.
""",
    "confidence": f"""You are an expert evaluator tasked exclusively with providing concise numerical probability estimates for outcomes of physics simulations.

{SIMULATION_CONDITIONS}

**Task:** Given an initial image, estimate the probability that the specified objective is successfully achieved.

**Response format:** Provide ONLY a numerical percentage (e.g., "85%"). Do NOT include explanations, reasoning, or any other additional text.""",
    "interactive": f"""You are a physics expert creating solutions for physics simulations.

{SIMULATION_CONDITIONS}

**Task:**
Your objective is to place a new ball inside the simulation area to achieve the specified goal.
Clearly define your solution by specifying:
- "x": horizontal position of the ball center (0 is left, maximum is {SCENE_DIMENSIONS[0]} on the right)
- "y": vertical position of the ball center (0 is bottom, maximum is {SCENE_DIMENSIONS[1]} at the top)
- "radius": size of the ball (minimum {MIN_RADIUS}, maximum {MAX_RADIUS})

**Important rules for placing the ball:**
- The ball **must remain fully within the visible simulation boundaries**.
- The ball **cannot overlap with existing objects**.

**Response format (always follow exactly):**
Provide your solution strictly in the following JSON format:

```json
{{
  "x": "<x-coordinate>",
  "y": "<y-coordinate>",
  "radius": "<ball_radius>"
}}
```""",
    "interactive_two_ball": f"""You are a physics expert creating solutions for physics simulations.

{SIMULATION_CONDITIONS}

**Task:**
Your objective is to place **TWO** new balls inside the simulation area to achieve the specified goal.
Clearly define your solution by specifying for each ball:
- "x": horizontal position of the ball center (0 is left, maximum is {SCENE_DIMENSIONS[0]} on the right)
- "y": vertical position of the ball center (0 is bottom, maximum is {SCENE_DIMENSIONS[1]} at the top)
- "radius": size of the ball (minimum {MIN_RADIUS}, maximum {MAX_RADIUS})

**Important rules for placing the balls:**
- Each ball **must remain fully within the visible simulation boundaries**.
- Each ball **cannot overlap with existing objects or with each other**.

**Response format (always follow exactly):**
Provide your solution strictly in the following JSON format:

```json
[
  {{
    "x": "<x-coordinate-ball-1>",
    "y": "<y-coordinate-ball-1>",
    "radius": "<ball-1-radius>"
  }},
  {{
    "x": "<x-coordinate-ball-2>",
    "y": "<y-coordinate-ball-2>",
    "radius": "<ball-2-radius>"
  }}
]
```""",
}

# User prompt templates for different levels of instruction detail
USER_TEMPLATES = {
    "sanity_check": "Based on the current state, are the <TARGET_OBJ1> and <TARGET_OBJ2> in contact?",
    "binary": f"Will the <TARGET_OBJ1> and <TARGET_OBJ2> come into contact for {CONTACT_DURATION} seconds?",
    "ranking": f"""Will the <TARGET_OBJ1> and <TARGET_OBJ2> come into contact for {CONTACT_DURATION} seconds?

Rank the proposals by their likelihood of success:
""",
    "confidence": f"""What is the probability that the <TARGET_OBJ1> and <TARGET_OBJ2> will come into contact for {CONTACT_DURATION} seconds?

Answer:""",
    "interactive": "Try 1:",
    "interactive_two_ball": "Try 1:",
}

# Interactive response templates for different evaluation outcomes
INTERACTIVE_RESPONSE_TEMPLATES = {
    "OUTSIDE_BOUNDARIES": """Your previous proposal couldn't be applied.

**Reason**: Your ball exceeds the simulation boundaries.

**Try again**, ensuring the ball fits entirely within the boundaries (0 ≤ x ≤ 256, 0 ≤ y ≤ 256). Provide a new proposal strictly in the same JSON format.

Try {attempt}:""",
    "OUTSIDE_BOUNDARIES_TWO_BALL": """Your previous proposal couldn't be applied.

**Reason**: One or both of your balls exceed the simulation boundaries.

**Try again**, ensuring both balls fit entirely within the boundaries (0 ≤ x ≤ 256, 0 ≤ y ≤ 256). Provide a new proposal strictly in the same JSON format.

Try {attempt}:""",
    "OVERLAPPING": """Your previous proposal couldn't be applied.

**Reason**: Your ball overlaps existing objects.

**Try again**, ensuring the ball does not overlap with any other object. Provide a new proposal strictly in the same JSON format.

Try {attempt}:""",
    "OVERLAPPING_TWO_BALL": """Your previous proposal couldn't be applied.

**Reason**: One or both of your balls overlap with existing objects or with each other.

**Try again**, ensuring neither ball overlaps with any existing object or with each other. Provide a new proposal strictly in the same JSON format.

Try {attempt}:""",
    "GOAL_NOT_REACHED": """The simulation ran successfully, but your proposal didn't achieve the goal.

Review the following 5 simulation frames, each sampled at regular intervals, that illustrate key stages in the evolution of your previous proposal.

[IMAGES]

Carefully analyze the frames and **try again**. Provide a new proposal strictly in the same JSON format.

Try {attempt}:""",
    "GOAL_REACHED": """Congratulations! Your proposal successfully achieved the goal.
The simulation shows that the target objects came into contact as required.""",
    "JSON_INCORRECT_FORMAT": """Your previous proposal couldn't be applied.

**Reason**: The JSON format in your response is incorrect or missing.

**Try again**, ensuring you provide a valid JSON object with the required fields (x, y, radius) in the following format:
```json
{
  "x": 100,
  "y": 150,
  "radius": 15
}
```

Try {attempt}:""",
    "JSON_INCORRECT_FORMAT_TWO_BALL": """Your previous proposal couldn't be applied.

**Reason**: The JSON format in your response is incorrect or missing.

**Try again**, ensuring you provide a valid JSON array with two objects, each containing the required fields (x, y, radius) in the following format:
```json
[
  {
    "x": 100,
    "y": 150,
    "radius": 15
  },
  {
    "x": 200,
    "y": 100,
    "radius": 10
  }
]
```

Try {attempt}:""",
}
