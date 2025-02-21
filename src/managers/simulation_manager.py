from dataclasses import dataclass

import numpy as np
import pygame
import pymunk
from Box2D import b2Contact, b2ContactListener, b2World
from loguru import logger
from PIL import Image

from ..classes.shapes import create_pybox2d_body, create_pymunk_body
from ..utils.const import (
    COLLISION_DURATION_THRESHOLD,
    DEFAULT_Y_GRAVITY,
    FPS,
    MAX_STEPS,
    STOP_DURATION_THRESHOLD,
    STOP_VELOCITY_THRESHOLD,
    TIME_SCALE,
)
from .base_manager import BaseManager
from .pygame_manager import PygameManager


@dataclass
class SimulationManager(BaseManager):
    """
    Simulation Manager based on PyMunk.
    """

    def run_simulation(
        self,
        puzzle: dict,
        visualize: bool = False,
        get_screenshot: bool = False,
        y_gravity: float = DEFAULT_Y_GRAVITY,
        max_steps: int = MAX_STEPS,
        time_scale: float = TIME_SCALE,
        fps: int = FPS,
        collision_duration_threshold: int = COLLISION_DURATION_THRESHOLD,
        stop_duration_threshold: int = STOP_DURATION_THRESHOLD,
    ) -> tuple[bool, Image.Image | None]:
        """
        Runs a PyMunk simulation of the given puzzle configuration.

        Returns:
            (collision_goal_reached, screenshot)
            collision_goal_reached: bool
            screenshot: PIL Image or None
        """
        gravity = (0, -DEFAULT_Y_GRAVITY)
        world = b2World(gravity=gravity, doSleep=True)

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

        # -- 4) Visualization & optional screenshot --
        renderer = None
        screenshot = None
        if visualize or get_screenshot:
            renderer = PygameManager()

            if get_screenshot:
                renderer.render(space)
                arr = pygame.surfarray.array3d(renderer.screen)
                arr = np.transpose(arr, (1, 0, 2))
                screenshot = Image.fromarray(arr)

        # -- 5) Main simulation loop --
        static_counter = 0
        for step_i in range(max_steps):
            space.step(time_scale / fps)  # integrate

            # Render if needed
            if visualize and renderer:
                keep_going = renderer.render(space)
                if not keep_going:
                    break  # user closed window

            if collision_goal["colliding"]:
                collision_goal["frames"] += 1
            else:
                collision_goal["frames"] = 0

            # Check if collision has lasted enough frames
            if collision_goal["frames"] >= collision_duration_threshold:
                collision_goal["reached"] = True
                logger.debug("Targets collided for the required duration!")
                break

            # Check if system is static
            if self._is_world_static(space):
                static_counter += 1
                if static_counter > stop_duration_threshold:
                    logger.debug("World is static; stopping simulation early.")
                    break
            else:
                static_counter = 0

        if renderer:
            renderer.quit()

        return collision_goal["reached"], screenshot

    def _is_world_static(
        self,
        space: pymunk.Space,
        stop_velocity_threshold: float = STOP_VELOCITY_THRESHOLD,
    ) -> bool:
        """
        Check if all dynamic bodies in the space have velocity below threshold.
        """
        for body in space.bodies:
            if body.body_type == pymunk.Body.DYNAMIC:
                vx, vy = body.velocity
                if (
                    abs(vx) > stop_velocity_threshold
                    or abs(vy) > stop_velocity_threshold
                    or abs(body.angular_velocity) > stop_velocity_threshold
                ):
                    return False
        return True
