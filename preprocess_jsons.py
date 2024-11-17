import shutil
from pathlib import Path


def create_folders(base_path: Path) -> None:
    """Create 1_ball and 2_ball folders."""
    (base_path / "categories" / "1_ball").mkdir(exist_ok=True)
    (base_path / "categories" / "2_ball").mkdir(exist_ok=True)


def get_json_files(data_path: Path) -> list[Path]:
    """Get all JSON files from the data folder."""
    return sorted(data_path.glob("*.json"))


def process_files(files, base_path: Path) -> None:
    """Process and move files to the appropriate folders."""
    level_files = {}

    for file in files:
        level, iteration = map(int, file.stem.split("_"))
        if level not in level_files:
            level_files[level] = []
        level_files[level].append(file)

    for level, files in level_files.items():
        ball_folder = "1_ball" if level < 100 else "2_ball"
        level_folder = base_path / ball_folder / f"{level:05d}"
        level_folder.mkdir(parents=True, exist_ok=True)

        for new_iteration, file in enumerate(files):
            iteration_folder = level_folder / f"{new_iteration:02d}"
            iteration_folder.mkdir(parents=True, exist_ok=True)
            shutil.move(file, iteration_folder / "data.json")


def main() -> None:
    base_path = Path("data")
    create_folders(base_path)
    files = get_json_files(base_path)
    process_files(files, base_path)


if __name__ == "__main__":
    main()
