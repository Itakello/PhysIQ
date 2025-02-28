# Simulation constants
SCREEN_SCALE_FACTOR = 3
RESOLUTION_SCALE_FACTOR = 5
FPS = 60
TIME_SCALE = 1
STOP_VELOCITY_THRESHOLD = 0.1
FRAMES_FOR_STATIC_EARLY_STOP = 400
MAX_STEPS = 3000
GOAL_COLLISIONS_REQUIRED = 360

# Physics constants
SCENE_DIMENSIONS = (256, 256)
DEFAULT_Y_GRAVITY = 9.81
DEFAULT_DENSITY = 0.25
DEFAULT_FRICTION = 0.5
DEFAULT_ELASTICITY = 0.20
DEFAULT_ANGULAR_DAMPING = 0.01
DEFAULT_LINEAR_DAMPING = 0.0
VELOCITY_ITERATIONS = 10
POSITION_ITERATIONS = 10

# Solutions constants
MIN_RADIUS = 2
MAX_RADIUS = SCENE_DIMENSIONS[1] // 8
MAX_ATTEMPTS = 10000

# Body types
STATIC_BODY = 0
DYNAMIC_BODY = 1
KINEMATIC_BODY = 2

# Common color references
COLORS = {
    0: "red",
    1: "black",
    2: "green",
    3: "azure",
    4: "purple",
    5: "grey",
    6: "black",
}

# Shape types
POLYGON = 0
CIRCLE = 1
EDGE = 2
CUSTOM = 3

# Relationship types
RELATIONSHIP_CONTACT = 0  # Objects in contact
RELATIONSHIP_DISTANCE = 1  # Distance between objects
RELATIONSHIP_ORIENTATION = 2  # Relative orientation

# Key object types for prompt formatting
TARGET_OBJECTS = {
    "BALL": "ball",
    "RECTANGLE": "rectangle",
    "TRIANGLE": "triangle",
    "PLATFORM": "platform",
}

# Maximum number of bodies to include in detailed description
MAX_BODIES_TO_DESCRIBE = 5
