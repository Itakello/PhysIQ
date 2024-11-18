import random
from dataclasses import dataclass, field

import pygame
from itakello_logging import ItakelloLogging

from ..classes.proposal import Proposal
from ..classes.shapes.circle import Circle
from ..classes.task import Task
from ..config import config
from .base_manager import BaseManager
from .surface_manager import SurfaceManager

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class SimulationManager(BaseManager):
    show_visualization: bool = True
    task: Task = field(init=False)
    surface_manager: SurfaceManager = field(default_factory=SurfaceManager)

    def __post_init__(self) -> None:
        pygame.init()
        self.surface_manager.create_surfaces()

    def load_task(self, task: Task) -> bool:
        pygame.display.set_caption(
            f"Pymunk Simulation - {task.category}:{task.id}:{task.idx}"
        )
        # if self.show_visualization:
        task.space.link_screen(self.surface_manager.sim_surface)
        self.task = task
        self.task.space.elapsed_time = 0.0
        logger.confirmation(f"Loaded task: {task}")

        return True

    def test_goal(self) -> tuple[bool, pygame.Surface | None, pygame.Surface | None]:
        fixed_dt = (1.0 / config.FPS) * config.TIME_SCALE
        starting_screen = None
        ending_screen = None

        while True:
            self.task.space.elapsed_time += fixed_dt

            if self.show_visualization or starting_screen is None:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return (False, starting_screen, ending_screen)

                self.surface_manager.clear_sim_surface()

            if starting_screen is None:
                self._display_surface()
                starting_screen = self.surface_manager.get_snapshot()
            elif self.show_visualization:
                self._display_surface()

            if self.task.handler.data["goal_reached"]:
                if not self.show_visualization:
                    self.surface_manager.clear_sim_surface()
                self._display_surface()
                return (True, starting_screen, self.surface_manager.get_snapshot())

            # Time limit check
            if self.task.space.elapsed_time >= config.SIMULATION_DURATION_THRESHOLD:
                if not self.show_visualization:
                    self.surface_manager.clear_sim_surface()
                self._display_surface()
                return (False, starting_screen, self.surface_manager.get_snapshot())

            self.task.space.step(fixed_dt)

    def find_proposals(self, config_name: str) -> None:
        attempts = 0
        counter_good_candidates = 0
        counter_bad_candidates = 0
        proposals = []
        while (
            attempts < config.MAX_ATTEMPTS
            or counter_good_candidates < config.NUMBER_OF_GOOD_CANDIDATES
            or counter_bad_candidates < config.NUMBER_OF_BAD_CANDIDATES
        ):
            ball = self._create_random_ball()

            # Check for collisions with existing bodies
            if not self.task.space.check_collisions(ball):
                self.task.space.add_body(ball)
                logger.debug(f"Found valid position for ball at attempt: {attempts}")
                accomplished, start_screen, end_screen = self.test_goal()
                assert start_screen
                assert end_screen
                if accomplished:
                    if counter_good_candidates < config.NUMBER_OF_GOOD_CANDIDATES:
                        logger.confirmation(
                            f"Found GOOD proposal at attempt: {attempts}"
                        )
                        proposals.append(
                            Proposal(
                                idx=counter_good_candidates,
                                bodies=[ball],
                                start_screen=start_screen,
                                end_screen=end_screen,
                                good=True,
                            )
                        )
                        counter_good_candidates += 1
                else:
                    if counter_bad_candidates < config.NUMBER_OF_BAD_CANDIDATES:
                        logger.confirmation(
                            f"Found BAD proposal at attempt: {attempts}"
                        )
                        proposals.append(
                            Proposal(
                                idx=counter_bad_candidates,
                                bodies=[ball],
                                start_screen=start_screen,
                                end_screen=end_screen,
                                good=False,
                            )
                        )
                        counter_bad_candidates += 1
                self.reset_task()
                if (
                    counter_good_candidates >= config.NUMBER_OF_GOOD_CANDIDATES
                    and counter_good_candidates >= config.NUMBER_OF_BAD_CANDIDATES
                ):
                    break
            attempts += 1

        self.task.save_proposals(config_name, proposals)

        if attempts >= config.MAX_ATTEMPTS:
            logger.warning(
                "Could not find valid position for random ball after max attempts"
            )
        return

    def reset_task(self) -> None:
        """Reset the current task to its initial state."""
        self.task.reset()

        # Ensure visualization is properly set up
        if self.show_visualization:
            self.task.space.link_screen(self.surface_manager.sim_surface)

        logger.debug(f"Reset task: {self.task}")

    def _display_surface(self) -> None:
        self.task.space.draw()
        self.surface_manager.scale_and_display()

    def _create_random_ball(self) -> Circle:
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
        return ball
