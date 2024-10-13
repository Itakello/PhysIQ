import pymunk

# Create a space
space = pymunk.Space()

# Set gravity (note the negative y-value)
space.gravity = pymunk.Vec2d(0, -98.1)

# Set up default body properties
body_properties = {
    "density": 1.0,
    "friction": 0.5,
    "elasticity": 0.3,  # Pymunk uses elasticity instead of restitution
}


# Function to create a body with default properties
def create_body(body_type, **kwargs):
    body = pymunk.Body(body_type=body_type)
    body.velocity_func = lambda body, gravity, damping, dt: pymunk.Body.update_velocity(
        body, gravity, 1.0, dt
    )
    shape = pymunk.Poly.create_box(body, **kwargs)
    for key, value in body_properties.items():
        setattr(shape, key, value)
    return body, shape


# Set up simulation parameters
dt = 1.0 / 60.0  # Time step (1/FPS)


# Simulation loop
def simulate(space, num_steps):
    for _ in range(num_steps):
        space.step(dt)
