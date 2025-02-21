from dataclasses import dataclass

import numpy as np
import pygame
from Box2D import b2_staticBody, b2Contact, b2ContactListener, b2World
from loguru import logger
from PIL import Image

from ..classes.shapes import create_pybox2d_body
from ..utils.const import (
    COLLISION_DURATION_THRESHOLD,
    DEFAULT_Y_GRAVITY,
    FPS,
    MAX_STEPS,
    POSITION_ITERATIONS,
    STOP_VELOCITY_THRESHOLD,
    TIME_SCALE,
    VELOCITY_ITERATIONS,
)
from .base_manager import BaseManager
from .pygame_manager import PygameManager


class CollisionListener(b2ContactListener):
    """
    Custom collision listener that records collisions between two specific body indices.
    We identify the colliding bodies by matching fixture.userData or body.userData.
    Tracks collision duration to ensure it meets the threshold requirement.
    """

    def __init__(self) -> None:
        super().__init__()
        self.goal_reached = False
        self.collision_start_frame = None
        self.current_frame = 0
        self.is_colliding = False

    def BeginContact(self, contact: b2Contact) -> None:
        """Start tracking collision duration when target bodies collide."""
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        if bodyA_id is not None and bodyB_id is not None:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.is_colliding = True
                if self.collision_start_frame is None:
                    self.collision_start_frame = self.current_frame

    def EndContact(self, contact: b2Contact) -> None:
        """Reset collision tracking when target bodies separate."""
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        if bodyA_id is not None and bodyB_id is not None:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.is_colliding = False
                self.collision_start_frame = None

    def update(self) -> None:
        """Update frame counter and check if collision duration meets threshold."""
        self.current_frame += 1

        if self.is_colliding and self.collision_start_frame is not None:
            collision_duration = self.current_frame - self.collision_start_frame
            if collision_duration >= COLLISION_DURATION_THRESHOLD:
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
        collision_duration_threshold: int = COLLISION_DURATION_THRESHOLD,
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
        for step_i in range(max_steps):
            world.Step(time_scale / fps, VELOCITY_ITERATIONS, POSITION_ITERATIONS)

            # Render if needed
            if visualize and renderer:
                keep_going = renderer.render(world)
                if not keep_going:
                    break  # user closed window

            if collision_listener.goal_reached:
                logger.debug("Collision goal reached.")
                break

            # Check if system is static
            if self._is_world_static(world):
                static_counter += 1
                if static_counter > collision_duration_threshold:
                    logger.debug("World is static; stopping simulation early.")
                    break
            else:
                static_counter = 0

        if renderer:
            renderer.quit()

        return collision_listener.goal_reached, screenshot
