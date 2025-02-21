import argparse

from Box2D import b2Contact, b2ContactListener, b2World
from loguru import logger

from src.classes.shapes import create_pybox2d_body
from src.managers.db_manager import MongoDBManager, SimulationManager
from src.utils.const import (
    DEFAULT_Y_GRAVITY,
    FPS,
    MAX_SIMULATION_STEPS,
    POSITION_ITERATIONS,
    TIME_SCALE,
    VELOCITY_ITERATIONS,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run PyBox2D simulations on puzzle templates from MongoDB."
    )
    parser.add_argument(
        "--start_template",
        type=int,
        default=0,
        help="Index of the first template to test",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of puzzle iterations to test per template",
    )
    parser.add_argument(
        "--db_name",
        type=str,
        default="physiq_db",
        help="Name of the MongoDB database to connect to",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Enable Pygame visualization of the simulation",
    )
    return parser.parse_args()


def run_box2d_simulation(puzzle: dict, visualize: bool = False) -> bool:
    gravity = (0, -DEFAULT_Y_GRAVITY)
    world = b2World(gravity=gravity, doSleep=True)

    collision_listener = CollisionListener()
    world.contactListener = collision_listener

    # Create bodies ONCE
    for idx, bd in enumerate(puzzle["bodies"]):
        is_target = (idx == puzzle["relationship"]["bodyId1"]) or (
            idx == puzzle["relationship"]["bodyId2"]
        )
        create_pybox2d_body(world, bd, body_index=idx, is_target=is_target)

    # Only do this if we want visualization
    renderer = None
    if visualize:
        from src.utils.pygame_renderer import PygameRenderer

        renderer = PygameRenderer()

    # Simulation loop
    for step_i in range(MAX_SIMULATION_STEPS):
        world.Step(TIME_SCALE / FPS, VELOCITY_ITERATIONS, POSITION_ITERATIONS)

        if visualize:
            # Render the entire Box2D world
            if not renderer.render(world):
                # User closed the pygame window
                break

        if collision_listener.goal_reached:
            break

    if renderer:
        renderer.quit()

    return collision_listener.goal_reached


def main(args: argparse.Namespace) -> None:
    # Connect to DB
    db_manager = MongoDBManager(db_name=args.db_name)

    grouped_templates = db_manager.get_grouped_templates(
        args.start_template, args.iterations
    )

    simulation_manager = SimulationManager()

    for template_id, puzzles in grouped_templates.items():
        if not puzzles:
            logger.info(f"No tasks found for template {template_id}")
            continue

        logger.info(f"Simulating template {template_id} with {len(puzzles)} tasks")

        for puzzle_doc in puzzles:
            pid = puzzle_doc["id"]
            collided, _ = simulation_manager.run_simulation(
                puzzle_doc, visualize=args.visualize, get_screenshot=False
            )
            logger.info(f"Puzzle {pid} => Collided? {collided}")

    db_manager.close_connection()
    logger.info("Done running simulations!")


if __name__ == "__main__":
    args = parse_args()
    main(args)
