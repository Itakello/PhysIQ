import random
from dataclasses import dataclass, field

import pygame
from itakello_logging import ItakelloLogging

from ..classes.shapes.circle import Circle
from ..classes.task import Task
from ..config import config
from .base_manager import BaseManager
from .surface_manager import SurfaceManager

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class SimulationManager(BaseManager):
    elapsed_time: float = 0.0
    show_visualization: bool = True
    task: Task = field(init=False)
    clock: pygame.time.Clock = field(default_factory=pygame.time.Clock)
    surface_manager: SurfaceManager = field(default_factory=SurfaceManager)

    def __post_init__(self) -> None:
        pygame.init()
        self.surface_manager.create_surfaces()

    def load_task(self, task: Task) -> bool:
        pygame.display.set_caption(
            f"Pymunk Simulation - {task.category}:{task.id}:{task.idx}"
        )

        assert self.surface_manager.sim_surface
        task.link_screen(self.surface_manager.sim_surface)
        self.task = task
        self.elapsed_time = 0.0
        logger.confirmation(f"Loaded task: {task}")

        return True

    def toggle_visualization(self) -> None:
        """Toggle the visualization state."""
        self.show_visualization = not self.show_visualization
        logger.confirmation(
            f"Visualization {'enabled' if self.show_visualization else 'disabled'}"
        )

    def test_goal(self) -> bool:
        fixed_time_step = 1.0 / config.FPS
        scaled_time_step = fixed_time_step * config.TIME_SCALE

        while True:
            dt = self.clock.tick(config.FPS) / 1000.0
            self.elapsed_time += dt

            if self.show_visualization:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return False

                self.surface_manager.clear_sim_surface()

            # Physics simulation steps
            for _ in range(config.SIMULATION_STEPS_PER_FRAME):
                self.task.space.step(scaled_time_step)

            # Visualization updates
            if self.show_visualization:
                self.task.space.draw()
                self.surface_manager.scale_and_display()

            # Time limit check
            if self.elapsed_time >= config.SIMULATION_EXAMPLE_DURATION:
                return False

    def find_proposal(self) -> None:
        attempt = 0
        while attempt < config.MAX_ATTEMPTS:
            radius = random.uniform(config.MIN_RADIUS, config.MAX_RADIUS)
            # Position considers radius to keep ball within bounds
            x = random.uniform(radius, config.SCENE_DIMENSIONS[0] - radius)
            y = random.uniform(radius, config.SCENE_DIMENSIONS[1] - radius)

            # Create ball configuration
            ball_config = {
                "bodyType": 1,
                "shapeType": 1,
                "position": [x, y],
                "radius": radius,
                "color": 1,
                "mass": 1.0,
            }

            # Create the shape
            ball = self.task.create_body(len(self.task.bodies) + 1, ball_config)
            assert type(ball) is Circle

            # Check for collisions with existing bodies
            if not self.task.space.check_collisions(ball):
                self.task.space.add_body(ball)
                logger.confirmation(
                    f"Found valid position for ball at attempt: {attempt}"
                )
                if self.test_goal():
                    logger.confirmation(f"Found correct proposal at attempt: {attempt}")
                    return
                else:
                    self.task.space.remove_body(ball)

            attempt += 1

        logger.warning(
            "Could not find valid position for random ball after max attempts"
        )
        return None
