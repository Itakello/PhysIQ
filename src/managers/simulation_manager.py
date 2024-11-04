import random  # Add this import
from dataclasses import dataclass, field

import pygame
from itakello_logging import ItakelloLogging

from ..config import config
from .base_manager import BaseManager
from .button_manager import ButtonManager
from .config_manager import ConfigManager
from .level_manager import LevelManager
from .shape_manager import ShapeManager
from .space_manager import SpaceManager
from .surface_manager import SurfaceManager

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class SimulationManager(BaseManager):
    is_running: bool = True
    elapsed_time: float = 0.0
    created_ball: bool = False
    clock: pygame.time.Clock = field(default_factory=pygame.time.Clock)
    space_manager: SpaceManager = field(default_factory=SpaceManager)
    shape_manager: ShapeManager = field(default_factory=ShapeManager)
    level_manager: LevelManager = field(default_factory=LevelManager)
    config_manager: ConfigManager = field(default_factory=ConfigManager)
    surface_manager: SurfaceManager = field(default_factory=SurfaceManager)
    button_manager: ButtonManager = field(default_factory=ButtonManager)

    def setup(self) -> None:
        pygame.init()
        self.level_manager.load_levels()
        """self.button_manager.add_button(10, 10, 100, 50, "Stop").on_click = (
            self.toggle_simulation
        )"""

    def run(self) -> None:
        fixed_time_step = 1.0 / config.FPS
        scaled_time_step = fixed_time_step * config.TIME_SCALE
        running = self._load_next_level()
        while running:
            if self.is_running:
                dt = self.clock.tick(config.FPS) / 1000.0  # Convert to seconds
                self.elapsed_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.button_manager.handle_event(event)

            self.surface_manager.clear_sim_surface()

            if self.is_running:
                for _ in range(config.SIMULATION_STEPS_PER_FRAME):
                    self.space_manager.custom_space.step(scaled_time_step)

            if not self.created_ball and self.elapsed_time > 5:
                self.create_random_ball()
                self.created_ball = True

            self.space_manager.custom_space.draw()
            self.surface_manager.scale_and_display()

            running = self._check_and_load_next_level()

        # Ensure pygame is quit at the end
        pygame.quit()
        logger.confirmation("Simulation completed")

    def create_random_ball(self) -> bool:

        assert self.surface_manager.sim_surface
        scene_width, scene_height = self.surface_manager.sim_surface.get_size()
        scene_width /= config.SCREEN_SCALE_FACTOR + 2
        scene_height /= config.SCREEN_SCALE_FACTOR + 2

        for attempt in range(config.MAX_ATTEMPTS):
            radius = random.uniform(config.MIN_RADIUS, config.MAX_RADIUS)
            # Position considers radius to keep ball within bounds
            x = random.uniform(radius, scene_width - radius)
            y = random.uniform(radius, scene_height - radius)

            # Create ball configuration
            ball_config = {
                "bodyType": 1,
                "shapeType": 1,
                "position": [x, y],
                "diameter": radius * 2,
                "color": 1,
                "mass": 1.0,
            }

            # Create the shape
            ball_shape = self.shape_manager.create_shape(ball_config)

            # Check for collisions with existing bodies
            if not self.space_manager.check_shape_collision(ball_shape):
                self.space_manager.add_shapes([ball_shape])
                logger.debug(f"CREATED random ball at attempt: {attempt}")
                return True

        logger.warning(
            "Could not find valid position for random ball after max attempts"
        )
        return False

    """def toggle_simulation(self) -> None:
        self.is_running = not self.is_running
        toggle_button = self.button_manager.get_button(0)
        assert toggle_button
        toggle_button.text = "Play" if self.is_running else "Stop" """

    def _add_bodies(self, bodies_data: list[dict]) -> None:
        bodies = [self.shape_manager.create_shape(body) for body in bodies_data]
        self.space_manager.add_shapes(bodies)

    def _load_next_level(self) -> bool:
        # Clear the space and reset managers
        self.space_manager.clear_space()
        self.shape_manager.reset()

        level = self.level_manager.get_next_level()
        if not level:
            return False

        config_filename = self.level_manager.get_current_config_filename()
        if not config_filename:
            return False

        config_data = self.config_manager.load_config(config_filename)

        scene_dimensions = config_data["scene_dimensions"]
        self.surface_manager.create_surfaces(scene_dimensions)
        pygame.display.set_caption(f"Pymunk Simulation - {config_filename}")
        assert self.surface_manager.sim_surface
        self.space_manager.link_screen(self.surface_manager.sim_surface)

        self._add_bodies(config_data["bodies"])
        self.elapsed_time = 0.0
        logger.confirmation(f"Loaded level {self.level_manager.current_level_id}")
        return True

    def _check_and_load_next_level(self) -> bool:
        if self.elapsed_time >= config.SIMULATION_EXAMPLE_DURATION:
            self.created_ball = False
            return self._load_next_level()
        return True
