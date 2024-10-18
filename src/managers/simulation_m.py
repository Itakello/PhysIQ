from dataclasses import dataclass, field

import pygame

from src.config import config

from .base_m import BaseManager
from .shape_m import ShapeManager
from .space_m import SpaceManager


@dataclass
class SimulationManager(BaseManager):
    config_data: dict = field(default_factory=dict)
    config_filename: str = ""
    screen: pygame.Surface = field(init=False)
    sim_surface: pygame.Surface = field(init=False)
    clock: pygame.time.Clock = field(init=False, default=pygame.time.Clock())
    space_manager: SpaceManager = field(init=False)
    shape_manager: ShapeManager = field(init=False)

    def __post_init__(self) -> None:
        self.shape_manager = ShapeManager()
        self.space_manager = SpaceManager()
        super().__post_init__()

    def setup(self) -> None:
        pygame.init()
        scene_dimensions = self.config_data["scene_dimensions"]
        self.screen = pygame.display.set_mode(
            [dim * config.SCREEN_SCALE_FACTOR for dim in scene_dimensions]
        )
        self.sim_surface = pygame.Surface(
            [dim * config.RESOLUTION_SCALE_FACTOR for dim in scene_dimensions]
        )
        pygame.display.set_caption(f"Pymunk Simulation - {self.config_filename}")
        self.space_manager.link_screen(self.sim_surface)

    def create_shapes(self) -> None:
        bodies = self.config_data["bodies"]
        shapes = [self.shape_manager.create_shape(body) for body in bodies]
        self.space_manager.add_shapes(shapes)

    def run(self) -> None:
        fixed_time_step = 1.0 / config.FPS
        scaled_time_step = fixed_time_step * config.TIME_SCALE
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.sim_surface.fill((255, 255, 255))

            for _ in range(config.SIMULATION_STEPS_PER_FRAME):
                self.space_manager.custom_space.step(scaled_time_step)

            self.space_manager.custom_space.draw()

            pygame.transform.smoothscale(
                self.sim_surface, self.screen.get_size(), self.screen
            )

            pygame.display.flip()
            self.clock.tick(config.FPS)

        pygame.quit()
        # self.logger.("Simulation completed")
