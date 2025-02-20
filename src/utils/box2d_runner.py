import numpy as np
import pygame
from Box2D import b2_staticBody, b2World
from PIL import Image

from src.utils.const import (
    DEFAULT_Y_GRAVITY,
    FPS,
    MAX_SIMULATION_STEPS,
    POSITION_ITERATIONS,
    STOP_VELOCITY_THRESHOLD,
    TIME_SCALE,
    VELOCITY_ITERATIONS,
    FRAMES_FOR_STATIC,
)
from src.utils.pygame_renderer import PygameRenderer

from .collision_listener import CollisionListener


def _is_world_static(world: b2World) -> bool:
    """Check if all bodies in the world are effectively static."""
    for body in world.bodies:
        if body.type != b2_staticBody:  # Only check dynamic bodies
            if (
                abs(body.linearVelocity.x) > STOP_VELOCITY_THRESHOLD
                or abs(body.linearVelocity.y) > STOP_VELOCITY_THRESHOLD
                or abs(body.angularVelocity) > STOP_VELOCITY_THRESHOLD
            ):
                return False
    return True


def run_simulation(
    puzzle: dict,
    visualize: bool = False,
    get_screenshot: bool = False,
) -> tuple[bool, Image.Image | None]:
    """
    Creates a Box2D world from the puzzle data, runs the simulation until completion
    or until the time limit is reached. Returns True if a collision goal is reached
    (if collision_listener is provided), otherwise False. Raises ValueError if overlapping bodies are detected.
    """
    screenshot = None
    # 1) Create the Box2D world
    world = b2World(gravity=(0, -DEFAULT_Y_GRAVITY), doSleep=True)

    # 2) Create puzzle's bodies
    from src.classes.shapes import create_pybox2d_body

    bodies_data = puzzle["bodies"]
    relationship = puzzle["relationship"]
    target_ids = (relationship["bodyId1"], relationship["bodyId2"])

    for idx, bd in enumerate(bodies_data):
        is_target = (idx == target_ids[0]) or (idx == target_ids[1])
        check_overlapping = bd.get("proposal", False)
        new_body = create_pybox2d_body(
            world,
            bd,
            body_index=idx,
            is_target=is_target,
            check_overlapping=check_overlapping,
        )
        if check_overlapping and new_body is None:
            raise ValueError("Overlapping bodies detected in the puzzle.")

    world.contactListener = CollisionListener()

    # 4) Visualization
    renderer = None
    if visualize or get_screenshot:
        renderer = PygameRenderer()

    if get_screenshot and renderer:
        world.Step(0.0, VELOCITY_ITERATIONS, POSITION_ITERATIONS)
        renderer.render(world)
        arr = pygame.surfarray.array3d(renderer.surface)
        arr = np.transpose(arr, (1, 0, 2))
        screenshot = Image.fromarray(arr)

    # 5) Run main simulation loop
    is_collision_goal = False
    static_counter = 0  # Count frames where world is static
    for _step in range(MAX_SIMULATION_STEPS):
        world.Step(TIME_SCALE / FPS, VELOCITY_ITERATIONS, POSITION_ITERATIONS)
        if visualize and renderer:
            if not renderer.render(world):
                break

        world.contactListener.update()
        if world.contactListener.goal_reached:
            is_collision_goal = True
            break

        # Check if world is static
        if _is_world_static(world):
            static_counter += 1
            if (
                static_counter > FRAMES_FOR_STATIC
            ):  # Wait a few frames to confirm static state
                break
        else:
            static_counter = 0

    # Quit PyGame if used
    if renderer:
        renderer.quit()

    return is_collision_goal, screenshot
