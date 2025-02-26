from src.utils.const import PROMPT_DIRECT

# System prompt template for all types of prompts
SYSTEM_TEMPLATE = """You are a physics expert analyzing physics simulations.
Your task is to predict whether the goal will be achieved in a given physics simulation.
The simulation involves various objects with different properties (static or dynamic, shapes, etc.).
The goal is for two specific objects (TARGET_OBJ1 and TARGET_OBJ2) to <RELATION>.

<CUSTOM_DESCRIPTION>

Provide your prediction as either "Success" or "Failure".
"""

# User prompt templates for different levels of instruction detail
USER_TEMPLATES = {
    # Direct prompt - minimal instructions focused on prediction
    "direct": """Based on the physics simulation shown in the image, predict if the two objects (<TARGET_OBJ1> and <TARGET_OBJ2>) will <RELATION>.
    
    <FEW_SHOT>
    
    Please provide your prediction as a single word: "Success" or "Failure".""",
    # Detailed prompt - more context and explanation requested
    "detailed": """Analyze the physics simulation shown in the image. The goal is for the <TARGET_OBJ1> and <TARGET_OBJ2> to <RELATION>
    
    <CUSTOM_DESCRIPTION>
    
    <FEW_SHOT>
    
    Based on your understanding of physics, predict whether this goal will be achieved.
    Consider factors such as gravity, momentum, object positions, and potential obstacles.
    First provide your prediction as "Success" or "Failure", then briefly explain your reasoning.""",
    # Chain-of-Thought prompt - explicitly guides reasoning
    "cot": """Analyze the physics simulation shown in the image. The goal is for the <TARGET_OBJ1> and <TARGET_OBJ2> to <RELATION>.
    
    <CUSTOM_DESCRIPTION>
    
    <FEW_SHOT>
    
    Follow these steps to make your prediction:
    1. Identify the key objects in the simulation and their properties (static/dynamic, position, etc.)
    2. Analyze how gravity and physics will affect the movement of dynamic objects
    3. Consider potential trajectories and interactions between objects
    4. Determine if the <TARGET_OBJ1> and <TARGET_OBJ2> will <RELATION>
    
    Based on your analysis, first provide your prediction as "Success" or "Failure", then explain your reasoning step by step.""",
}

# Default template to use if not specified
USER_TEMPLATE = USER_TEMPLATES[PROMPT_DIRECT]
