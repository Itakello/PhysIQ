import random
import time
from dataclasses import dataclass, field

import pygame

from ..classes.proposal import Proposal
from ..classes.shapes_old.circle import Circle
from ..classes.task import Task
from ..classes.types.color import Color
from ..config import const
from .base_manager import BaseManager
from .surface_manager import SurfaceManager


@dataclass
class SimulationManager(BaseManager):
    run_config: dict
    show_visualization: bool = True
    task: Task = field(init=False)
    surface_manager: SurfaceManager = field(default_factory=SurfaceManager)
    total_good_candidates: int = field(init=False, default=0)
    total_bad_candidates: int = field(init=False, default=0)
    total_attempts: int = field(init=False, default=0)
    total_attempts: int = field(init=False, default=0)
    performed_tasks: int = field(init=False, default=0)
    skipped_tasks: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        # if self.show_visualization:
        pygame.init()
        self.surface_manager.create_surfaces()

    def load_task(self, task: Task) -> bool:
        pygame.display.set_caption(
            f"Pymunk Simulation - {task.category}:{task.template_id}:{task.idx}"
        )
        # if self.show_visualization:
        task.space.link_screen(self.surface_manager.sim_surface)
        self.task = task
        self.task.space.elapsed_time = 0.0
        logger.info(f"Loaded task: {task}")

        return True

    def test_goal(
        self,
        require_good_end_screen: bool = True,
        require_bad_end_screen: bool = True,
        save_screenshots: bool = False,
    ) -> tuple[bool, pygame.Surface | None, pygame.Surface | None]:
        fixed_dt = (1.0 / const.FPS) * self.run_config["time_scale"]
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

            # Check if the goal has been reached or the simulation has run for too long
            if (
                self.task.handler.data["goal_reached"]
                or self.task.space.elapsed_time >= const.SIMULATION_DURATION_THRESHOLD
            ):
                if save_screenshots:
                    if (
                        self.task.handler.data["goal_reached"]
                        and require_good_end_screen
                    ) or (
                        not self.task.handler.data["goal_reached"]
                        and require_bad_end_screen
                    ):
                        self.surface_manager.clear_sim_surface()
                        self._display_frame()
                        end_screen = self.surface_manager.get_snapshot()
                return (
                    self.task.handler.data["goal_reached"],
                    start_screen,
                    end_screen,
                )

            self.task.space.elapsed_time += fixed_dt
            self.task.space.step(fixed_dt)

    def find_proposals(
        self, run_config_name: str, save_screenshots: bool = False
    ) -> tuple[int, int, int]:
        attempts = 0
        n_good_candidates = 0
        n_bad_candidates = 0
        proposals = []
        while attempts < const.MAX_ATTEMPTS:
            # Add balls to the space
            balls = []
            while len(balls) < self.task.n_balls:
                ball = self._create_random_ball()
                if not self.task.space.check_collisions(ball):
                    self.task.space.add_body(ball)
                    balls.append(ball)

            # Test the goal
            logger.debug(f"Found valid position for ball at attempt: {attempts}")
            accomplished, start_screen, end_screen = self.test_goal(
                require_bad_end_screen=n_bad_candidates
                < const.NUMBER_OF_BAD_CANDIDATES,
                require_good_end_screen=n_good_candidates
                < const.NUMBER_OF_GOOD_CANDIDATES,
                save_screenshots=save_screenshots,
            )

            # Remove the balls
            for ball in balls:
                self.task.space.remove_body(ball)

            if accomplished:
                if n_good_candidates < const.NUMBER_OF_GOOD_CANDIDATES:
                    logger.confirmation(f"Found GOOD proposal at attempt: {attempts}")
                    proposals.append(
                        Proposal(
                            idx=n_good_candidates,
                            attempt=attempts,
                            bodies=balls,
                            start_screen=start_screen,
                            end_screen=end_screen,
                            good=True,
                        )
                    )
                    n_good_candidates += 1
            else:
                if n_bad_candidates < const.NUMBER_OF_BAD_CANDIDATES:
                    logger.confirmation(f"Found BAD proposal at attempt: {attempts}")
                    proposals.append(
                        Proposal(
                            idx=n_bad_candidates,
                            attempt=attempts,
                            bodies=balls,
                            start_screen=start_screen,
                            end_screen=end_screen,
                            good=False,
                        )
                    )
                    n_bad_candidates += 1
            self.reset_task()
            if (
                n_good_candidates >= const.NUMBER_OF_GOOD_CANDIDATES
                and n_bad_candidates >= const.NUMBER_OF_BAD_CANDIDATES
            ):
                break
            attempts += 1

        self.task.save_proposals(run_config_name, proposals)

        if attempts >= const.MAX_ATTEMPTS:
            self.skipped_tasks += 1
            logger.warning(
                "Could not find valid position for random ball after max attempts"
            )
        else:
            self.performed_tasks += 1
        wandb.log(
            {
                "tasks/good_candidates": n_good_candidates,
                "tasks/bad_candidates": n_bad_candidates,
                "tasks/attempts": attempts,
            }
        )
        self.total_attempts += attempts
        self.total_good_candidates += n_good_candidates
        self.total_bad_candidates += n_bad_candidates
        return attempts, n_good_candidates, n_bad_candidates

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
        radius = random.uniform(const.MIN_RADIUS, const.MAX_RADIUS)
        # Position considers radius to keep ball within bounds
        x = random.uniform(radius, const.SCENE_DIMENSIONS[0] - radius)
        y = random.uniform(radius, const.SCENE_DIMENSIONS[1] - radius)

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
