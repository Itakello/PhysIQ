import argparse

from Box2D import b2Contact, b2ContactListener, b2World
from loguru import logger

from src.classes.shapes import create_pybox2d_body
from src.managers.db_manager import MongoDBManager
from src.utils.const import (
    DEFAULT_Y_GRAVITY,
    FPS,
    MAX_SIMULATION_STEPS,
    POSITION_ITERATIONS,
    TIME_SCALE,
    VELOCITY_ITERATIONS,
)


class CollisionListener(b2ContactListener):
    """
    Custom collision listener that records collisions between two specific body indices.
    We identify the colliding bodies by matching fixture.userData or body.userData.
    """

    def __init__(self):
        super().__init__()
        self.goal_reached = False

    def BeginContact(self, contact: b2Contact) -> None:
        """
        If the contact is between the two bodies of interest, mark the goal as reached.
        """
        fA = contact.fixtureA
        fB = contact.fixtureB

        if fA.userData is None or fB.userData is None:
            return

        # Suppose we store the puzzle’s “body_id” or some unique index
        bodyA_id = fA.userData.get("body_id")
        bodyB_id = fB.userData.get("body_id")

        # If these are the 2 bodies meant to collide
        if bodyA_id is not None and bodyB_id is not None:
            # If your puzzle design says "collide bodyId1 with bodyId2 to reach the goal"
            # then do something like:
            # e.g. if puzzle wants bodies #X, #Y to collide, match them here
            # For simplicity, let's check a quick condition:
            # (You could refine if you store or pass the puzzle's target IDs.)
            # We'll store them in the fixture userData (like "target": True), or do checks:
            if fA.userData.get("target") and fB.userData.get("target"):
                self.goal_reached = True

    def EndContact(self, contact: b2Contact) -> None:
        pass


def run_box2d_simulation(puzzle: dict, visualize: bool = False) -> bool:
    gravity = (0, -DEFAULT_Y_GRAVITY)
    world = b2World(gravity=gravity, doSleep=False)

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
    for _ in range(MAX_SIMULATION_STEPS):
        world.Step((1.0 / FPS) * TIME_SCALE, VELOCITY_ITERATIONS, POSITION_ITERATIONS)

        if visualize:
            # Render the entire Box2D world
            if renderer and not renderer.render(world):
                # User closed the pygame window
                break

        if collision_listener.goal_reached:
            break

    if renderer:
        renderer.quit()

    return collision_listener.goal_reached


def main() -> None:
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
    args = parser.parse_args()

    # Connect to DB
    db_manager = MongoDBManager(db_name=args.db_name)

    # Retrieve all puzzles, sort them by puzzle_id
    # puzzle_id typically looks like "00000:0" - we can parse the prefix as int
    puzzles_coll = db_manager.db["puzzles"]
    all_puzzles = list(puzzles_coll.find({}))

    # Sort by the integer part of puzzle_id before the colon
    def parse_template_id(pid: str) -> tuple[int, int]:
        # handle "00012:34" -> returns (12, 34)
        main_part, iteration_part = pid.split(":")
        return (int(main_part), int(iteration_part))

    all_puzzles.sort(key=lambda p: parse_template_id(p["puzzle_id"]))

    # Group by template_id
    grouped = {}
    for p in all_puzzles:
        template_part, iteration_part = parse_template_id(p["puzzle_id"])
        if template_part not in grouped:
            grouped[template_part] = []
        grouped[template_part].append(p)

    # Now iterate over template_part starting from start_template
    template_keys = sorted(list(grouped.keys()))
    for template_id in template_keys:
        if template_id < args.start_template:
            continue

        # We'll take up to "iterations" tasks from this template
        tasks = grouped[template_id][: args.iterations]
        if not tasks:
            logger.info(f"No tasks found for template {template_id}")
            continue

        logger.info(f"Simulating template {template_id} with {len(tasks)} tasks")

        for puzzle_doc in tasks:
            pid = puzzle_doc["puzzle_id"]
            puzzle_result = run_box2d_simulation(puzzle_doc, visualize=args.visualize)
            logger.info(f"Puzzle {pid} => Collided? {puzzle_result}")

            # Update DB with result
            puzzles_coll.update_one(
                {"_id": puzzle_doc["_id"]},
                {"$set": {"box2d_sim_result": puzzle_result}},
            )

    db_manager.close_connection()
    logger.info("Done running PyBox2D simulations!")


if __name__ == "__main__":
    main()
