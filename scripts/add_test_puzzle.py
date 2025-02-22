from src.managers import ArgparseManager, MongoDBManager, PuzzleManager


def main() -> None:
    parser = ArgparseManager("Add a test puzzle to the MongoDB database.")
    parser.add_common_db_args()
    args = parser.parse_args()

    db_manager = MongoDBManager(db_name=args.db_name)
    puzzle_manager = PuzzleManager()

    border_1 = puzzle_manager.create_polygon_body(
        position=[128.0, -2.5],
        vertices=[[128.0, 2.5], [-128.0, 2.5], [-128.0, -2.5], [128.0, -2.5]],
        body_type=0,
        color=6,
    )
    border_2 = puzzle_manager.create_polygon_body(
        position=[-2.5, 128.0],
        vertices=[[2.5, 128.0], [-2.5, 128.0], [-2.5, -128.0], [2.5, -128.0]],
        body_type=0,
        color=6,
    )
    border_3 = puzzle_manager.create_polygon_body(
        position=[128.0, 258.5],
        vertices=[[128.0, 2.5], [-128.0, 2.5], [-128.0, -2.5], [128.0, -2.5]],
        body_type=0,
        color=6,
    )

    border_4 = puzzle_manager.create_polygon_body(
        position=[258.5, 128.0],
        vertices=[[2.5, 128.0], [-2.5, 128.0], [-2.5, -128.0], [2.5, -128.0]],
        body_type=0,
        color=6,
    )
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
    puzzle = puzzle_manager.create_puzzle(
        [border_1, border_2, border_3, border_4, ball, platform], relationship, meta
    )
    db_manager.insert_puzzle(puzzle)


if __name__ == "__main__":
    main()
