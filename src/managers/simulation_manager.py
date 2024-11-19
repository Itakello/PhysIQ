import random
from dataclasses import dataclass, field
from pathlib import Path

import pygame
from itakello_logging import ItakelloLogging

from ..classes.custom_dict import CustomDict
from ..classes.proposal import Proposal
from ..classes.shapes.circle import Circle
from ..classes.task import Task
from ..classes.types.color import Color
from ..config import config
from .base_manager import BaseManager
from .surface_manager import SurfaceManager

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class SimulationManager(BaseManager):
    show_visualization: bool = True
    task: Task = field(init=False)
    surface_manager: SurfaceManager = field(default_factory=SurfaceManager)
    runs_configurations: CustomDict = field(init=False)

    def __post_init__(self) -> None:
        if self.show_visualization:
            pygame.init()
            self.surface_manager.create_surfaces()
        self.runs_configurations = CustomDict(
            file_name="runs_configuration.json",
            position=Path("data"),
        )

    def load_task(self, task: Task) -> bool:
        pygame.display.set_caption(
            f"Pymunk Simulation - {task.category}:{task.id}:{task.idx}"
        )
        if self.show_visualization:
            task.space.link_screen(self.surface_manager.sim_surface)
        self.task = task
        self.task.space.elapsed_time = 0.0
        logger.confirmation(f"Loaded task: {task}")

        return True

    def test_goal(
        self,
        run_config_name: str,
        require_end_screen: bool = True,
        save_screenshots: bool = False,
    ) -> tuple[bool, pygame.Surface | None, pygame.Surface | None]:
        current_run_config = self.runs_configurations["runs"][run_config_name]
        fixed_dt = (1.0 / config.FPS) * current_run_config["time_scale"]
        start_screen = None
        end_screen = None

        while True:
            if self.show_visualization or start_screen is None:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return (False, start_screen, end_screen)

                self.surface_manager.clear_sim_surface()

            if start_screen is None and save_screenshots:
                self._display_frame()
                start_screen = self.surface_manager.get_snapshot()
            elif self.show_visualization:
                self._display_frame()

            if self.task.handler.data["goal_reached"]:
                if self.show_visualization or save_screenshots:
                    self.surface_manager.clear_sim_surface()
                if save_screenshots:
                    self._display_frame()
                    end_screen = self.surface_manager.get_snapshot()
                return (True, start_screen, end_screen)

            # Time limit check
            if self.task.space.elapsed_time >= config.SIMULATION_DURATION_THRESHOLD:
                if require_end_screen:
                    if self.show_visualization:
                        self.surface_manager.clear_sim_surface()
                    if save_screenshots:
                        self._display_frame()
                        end_screen = self.surface_manager.get_snapshot()
                return (False, start_screen, end_screen)

            self.task.space.elapsed_time += fixed_dt
            self.task.space.step(fixed_dt)

    def find_proposals(
        self, run_config_name: str, save_screenshots: bool = False
    ) -> None:
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
                accomplished, start_screen, end_screen = self.test_goal(
                    run_config_name=run_config_name,
                    require_end_screen=counter_bad_candidates
                    < config.NUMBER_OF_BAD_CANDIDATES,
                    save_screenshots=save_screenshots,
                )
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
                    and counter_bad_candidates >= config.NUMBER_OF_BAD_CANDIDATES
                ):
                    break
            attempts += 1

        self.task.save_proposals(run_config_name, proposals)

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

    def _display_frame(self) -> None:
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
            "shapeType": Color.Preset.RED.value,
            "position": [x, y],
            "radius": radius,
            "color": 1,
            "mass": 1.0,
        }

        # Create the shape
        ball = self.task.create_body(len(self.task.bodies) + 1, ball_config)
        assert type(ball) is Circle
        return ball
