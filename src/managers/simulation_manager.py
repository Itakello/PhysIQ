from collections import deque
from dataclasses import dataclass

import numpy as np
import pygame
from Box2D import b2_staticBody, b2Contact, b2ContactListener, b2World
from loguru import logger
from PIL import Image

from ..classes.shapes import create_pybox2d_body
from ..utils.const import (
    COLLISION_WINDOW_SIZE,
    DEFAULT_Y_GRAVITY,
    FPS,
    FRAMES_FOR_STATIC_EARLY_STOP,
    MAX_STEPS,
    POSITION_ITERATIONS,
    REQUIRED_COLLISIONS,
    STOP_VELOCITY_THRESHOLD,
    TIME_SCALE,
    VELOCITY_ITERATIONS,
)
from .base_manager import BaseManager
from .pygame_manager import PygameManager


class CollisionListener(b2ContactListener):
    """
    Custom collision listener that records collision frequency between target bodies
    within a sliding window of frames.
    """

    def __init__(
        self,
        window_size: int = COLLISION_WINDOW_SIZE,
        required_collisions: int = REQUIRED_COLLISIONS,
    ) -> None:
        super().__init__()
        self.goal_reached = False
        self.current_frame = 0
        self.window_size = window_size
        self.required_collisions = required_collisions
        self.collision_history = deque([False] * window_size, maxlen=window_size)
        self.is_colliding = False

    def BeginContact(self, contact: b2Contact) -> None:
        """Record when target bodies start colliding."""
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        if bodyA_id is not None and bodyB_id is not None:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.is_colliding = True

    def EndContact(self, contact: b2Contact) -> None:
        """Record when target bodies stop colliding."""
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        if bodyA_id is not None and bodyB_id is not None:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.is_colliding = False

    def update(self) -> None:
        """
        Update collision history and check if collision frequency
        meets the threshold within the sliding window.
        """
        self.current_frame += 1
        self.collision_history.append(self.is_colliding)

        # Count collisions in the sliding window
        collisions_in_window = sum(1 for frame in self.collision_history if frame)
        if collisions_in_window >= self.required_collisions:
            self.goal_reached = True


@dataclass
class SimulationManager(BaseManager):
    """
    Simulation Manager based on PyMunk.
    """

    def _is_world_static(
        self, world: b2World, stop_velocity_threshold: float = STOP_VELOCITY_THRESHOLD
    ) -> bool:
        """Check if all bodies in the world are effectively static."""
        for body in world.bodies:
            if body.type != b2_staticBody:  # Only check dynamic bodies
                if (
                    abs(body.linearVelocity.x) > stop_velocity_threshold
                    or abs(body.linearVelocity.y) > stop_velocity_threshold
                    or abs(body.angularVelocity) > stop_velocity_threshold
                ):
                    return False
        return True

    def run_simulation(
        self,
        puzzle: dict,
        visualize: bool = False,
        get_screenshot: bool = False,
        y_gravity: float = DEFAULT_Y_GRAVITY,
        max_steps: int = MAX_STEPS,
        time_scale: float = TIME_SCALE,
        fps: int = FPS,
    ) -> tuple[bool, Image.Image | None]:
        world = b2World(gravity=(0, -y_gravity), doSleep=True)

        collision_listener = CollisionListener()
        world.contactListener = collision_listener

        for idx, body_data in enumerate(puzzle["bodies"]):
            is_target = (idx == puzzle["relationship"]["bodyId1"]) or (
                idx == puzzle["relationship"]["bodyId2"]
            )
            check_overlapping = body_data.get("proposal", False)  # same logic as before
            create_pybox2d_body(
                world,
                body_data,
                body_index=idx,
                is_target=is_target,
                check_overlapping=check_overlapping,
            )

        renderer = None
        screenshot = None
        if visualize or get_screenshot:
            renderer = PygameManager()

            if get_screenshot:
                renderer.render(world)
                arr = pygame.surfarray.array3d(renderer.screen)
                arr = np.transpose(arr, (1, 0, 2))
                screenshot = Image.fromarray(arr)

        # -- 5) Main simulation loop --
        static_counter = 0
        for _ in range(max_steps):
            world.Step(time_scale / fps, VELOCITY_ITERATIONS, POSITION_ITERATIONS)

            # Render if needed
            if visualize and renderer:
                keep_going = renderer.render(world)
                if not keep_going:
                    break  # user closed window

            world.contactListener.update()

            if world.contactListener.goal_reached:
                logger.debug("Collision goal reached.")
                break

            # Check if system is static
            if self._is_world_static(world):
                static_counter += 1
                if static_counter > FRAMES_FOR_STATIC_EARLY_STOP:
                    logger.debug("World is static; stopping simulation early.")
                    break
            else:
                static_counter = 0

        if renderer:
            renderer.quit()

        return world.contactListener.goal_reached, screenshot
