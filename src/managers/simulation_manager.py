from dataclasses import dataclass

from Box2D import b2_staticBody, b2World
from loguru import logger
from PIL import Image

from ..utils.collision_listener import CollisionListener
from ..utils.const import (
    DEFAULT_Y_GRAVITY,
    FPS,
    FRAMES_FOR_STATIC_EARLY_STOP,
    MAX_STEPS,
    POSITION_ITERATIONS,
    STOP_VELOCITY_THRESHOLD,
    TIME_SCALE,
    VELOCITY_ITERATIONS,
)
from .base_manager import BaseManager
from .pygame_manager import PygameManager
from .screenshot_manager import ScreenshotManager
from .shapes_manager import ShapesManager


@dataclass
class SimulationManager(BaseManager):
    shapes_manager: ShapesManager = ShapesManager()

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
        num_screenshots: int = 0,
        y_gravity: float = DEFAULT_Y_GRAVITY,
        max_steps: int = MAX_STEPS,
        time_scale: float = TIME_SCALE,
        fps: int = FPS,
    ) -> tuple[bool, list[Image.Image]]:
        # logger.debug(f"Running simulation for puzzle: {puzzle['id']}")
        world = b2World(gravity=(0, -y_gravity), doSleep=True)

        world.contactListener = CollisionListener()

        for idx, body_data in enumerate(puzzle["bodies"]):
            is_target = (idx == puzzle["relationship"]["bodyId1"]) or (
                idx == puzzle["relationship"]["bodyId2"]
            )
            check_overlapping = body_data.get("proposal", False)
            self.shapes_manager.create_body(
                world,
                body_data,
                body_index=idx,
                is_target=is_target,
                check_overlapping=check_overlapping,
            )

        renderer = None
        screenshots = []

        if visualize or num_screenshots > 0:
            renderer = PygameManager()

        static_counter = 0
        steps = 0

        while steps < max_steps:
            world.Step(time_scale / fps, VELOCITY_ITERATIONS, POSITION_ITERATIONS)

            # Render if needed
            if renderer:
                if visualize:
                    keep_going = renderer.render(world)
                    if not keep_going:
                        break  # user closed window
                if num_screenshots > 2 and steps % 60 == 0:
                    renderer.render(world)
                    screenshot = ScreenshotManager.take_screenshot(renderer.screen)
                    screenshots.append(screenshot)

            world.contactListener.update()

            if world.contactListener.goal_reached:
                logger.debug("Collision goal reached.")
                break

            # Check if system is static
            if self._is_world_static(world):
                static_counter += 1
                if static_counter > FRAMES_FOR_STATIC_EARLY_STOP:
                    # logger.debug("World is static; stopping simulation early.")
                    break
            else:
                static_counter = 0
            steps += 1

        if renderer and num_screenshots > 1:
            renderer.render(world)
            screenshot = ScreenshotManager.take_screenshot(renderer.screen)
            screenshots.append(screenshot)

        if renderer:
            renderer.quit()

        if (
            world.contactListener.collision_count
            > 0  # world.contactListener.required_collisions / 2
        ):
            logger.debug(
                f"Simulation {puzzle['id']} completed. Max collisions: {world.contactListener.collision_count}"
            )
        return world.contactListener.goal_reached, screenshots
