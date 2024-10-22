from dataclasses import dataclass, field

import pygame
from itakello_logging import ItakelloLogging

from ..config import config
from .base_m import BaseManager
from .button_m import ButtonManager
from .config_m import ConfigManager
from .level_m import LevelManager
from .shape_m import ShapeManager
from .space_m import SpaceManager

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class SimulationManager(BaseManager):
    is_running: bool = True
    config_data: dict = field(default_factory=dict)
    config_filename: str | None = None
    screen: pygame.Surface | None = None
    sim_surface: pygame.Surface | None = None
    clock: pygame.time.Clock = field(default_factory=pygame.time.Clock)
    space_manager: SpaceManager = field(default_factory=SpaceManager)
    shape_manager: ShapeManager = field(default_factory=ShapeManager)
    level_manager: LevelManager = field(default_factory=LevelManager)
    config_manager: ConfigManager = field(default_factory=ConfigManager)
    button_manager: ButtonManager = field(default_factory=ButtonManager)
    level_start_time: float = 0.0
    level_elapsed_time: float = 0.0

    def setup(self) -> None:
        pygame.init()
        self.level_manager.load_levels()
        self.button_manager.add_button(10, 10, 100, 50, "Stop").on_click = (
            self.toggle_simulation
        )

    def _load_next_level(self) -> bool:
        # Clear the space and reset managers
        self.space_manager.clear_space()
        self.shape_manager.reset()

        level = self.level_manager.get_next_level()
        if not level:
            return False

        self.config_filename = self.level_manager.get_current_config_filename()
        if not self.config_filename:
            return False

        self.config_data = self.config_manager.load_config(self.config_filename)

        scene_dimensions = self.config_data["scene_dimensions"]
        self.screen = pygame.display.set_mode(
            [dim * config.SCREEN_SCALE_FACTOR for dim in scene_dimensions]
        )
        self.sim_surface = pygame.Surface(
            [dim * config.RESOLUTION_SCALE_FACTOR for dim in scene_dimensions]
        )
        pygame.display.set_caption(f"Pymunk Simulation - {self.config_filename}")
        self.space_manager.link_screen(self.sim_surface)

        self.create_shapes()
        self.level_elapsed_time = 0.0
        logger.confirmation(f"Loaded level {self.level_manager.current_level_id}")
        return True

    def create_shapes(self) -> None:
        bodies = self.config_data["bodies"]
        shapes = [self.shape_manager.create_shape(body) for body in bodies]
        self.space_manager.add_shapes(shapes)

    def _check_and_load_next_level(self) -> bool:
        if self.level_elapsed_time >= 5.0:
            return self._load_next_level()
        return True

    def run(self) -> None:
        fixed_time_step = 1.0 / config.FPS
        scaled_time_step = fixed_time_step * config.TIME_SCALE
        running = self._load_next_level()
        while running:
            dt = self.clock.tick(config.FPS) / 1000.0  # Convert to seconds
            self.level_elapsed_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.button_manager.handle_event(event)

            if self.sim_surface:
                self.sim_surface.fill((255, 255, 255))

                if self.is_running:
                    for _ in range(config.SIMULATION_STEPS_PER_FRAME):
                        self.space_manager.custom_space.step(scaled_time_step)

                self.space_manager.custom_space.draw()
                self.button_manager.draw(self.sim_surface)

                if self.screen:
                    pygame.transform.smoothscale(
                        self.sim_surface, self.screen.get_size(), self.screen
                    )
                    pygame.display.flip()

            running = self._check_and_load_next_level()

        # Ensure pygame is quit at the end
        pygame.quit()
        logger.confirmation("Simulation completed")

    def toggle_simulation(self) -> None:
        self.is_running = not self.is_running
        toggle_button = self.button_manager.get_button(0)
        toggle_button.text = "Play" if self.is_running else "Stop"
