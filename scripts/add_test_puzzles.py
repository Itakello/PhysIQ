from src.managers import ArgparseManager, MongoDBManager, PuzzleManager
from src.utils.db_schemas import PuzzleSchema


def convert_to_test_puzzle(puzzle: PuzzleSchema) -> PuzzleSchema:
    """Convert a puzzle to a test puzzle by modifying its metadata."""
    puzzle.metadata.type = "TEST"
    return puzzle


def get_test_puzzle() -> PuzzleSchema:
    puzzle_manager = PuzzleManager(200, 0)
    ball = puzzle_manager.create_circle_body(
        position=[204.8, 242.9], radius=12.5, color=2, body_type=1
    )
    platform = puzzle_manager.create_polygon_body(
        position=[128.0, 2.56],
        vertices=[
            [128.0, 2.56],
            [-128.0, 2.56],
            [-128.0, -2.56],
            [128.0, -2.56],
        ],
        body_type=0,
        color=4,
    )
    relationship = puzzle_manager.create_relationship(
        body1_idx=4, body2_idx=5, relationships=[0]
    )
    meta = puzzle_manager.create_metadata(
        "Make sure the green ball is touching the purple bar.", tier="BALL", type="TEST"
    )
    puzzle = puzzle_manager.create_puzzle([ball, platform], relationship, meta)
    return puzzle


def main() -> None:
    parser = ArgparseManager("Add test puzzles to the MongoDB database.")
    parser.add_common_db_args()
    args = parser.parse_args()

    db_manager = MongoDBManager(db_name=args.db_name)

    # List of puzzles to convert (template_id, iteration_id)
    puzzles_to_convert = [
        (121, 3),
        (121, 4),
        (121, 5),
    ]

    for template_id, iteration_id in puzzles_to_convert:
        puzzle = db_manager.get_puzzle(template_id, iteration_id)
        if puzzle:
            test_puzzle = convert_to_test_puzzle(puzzle)
            db_manager.insert_puzzle(test_puzzle)

    # new_test_puzzle = get_test_puzzle()
    # db_manager.insert_puzzle(new_test_puzzle)

    db_manager.close_connection()


if __name__ == "__main__":
    main()
