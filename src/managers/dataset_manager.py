import random
from pathlib import Path
from typing import Any

from loguru import logger

from .mongodb_manager import MongoDBManager


class DatasetManager:
    """
    This manager handles retrieval of puzzle data, proposals (correct or incorrect),
    and the associated screenshots. It also supports optional few-shot retrieval
    (i.e., extra puzzle+proposal pairs) to insert into a prompt as exemplars.
    """

    def __init__(
        self,
        db_manager: MongoDBManager,
        images_base_dir: str | Path = "images",
    ):
        """
        Args:
            db_manager: Instance of MongoDBManager.
            images_base_dir: The base directory where images are stored,
                             e.g. "images/" containing "correct_proposals/" etc.
        """
        self.db_manager = db_manager
        self.images_base_dir = Path(images_base_dir)

    def get_sample(
        self,
        puzzle_id: str,
        proposal_tier: str = "CORRECT",
        num_frames: int = 2,
        few_shot_count: int = 0,
    ) -> dict[str, Any]:
        """
        Retrieve a single puzzle + proposal and (optionally) a few-shot list of additional puzzles.

        Args:
            puzzle_id: The puzzle identifier, e.g. "00012:001"
            proposal_tier: Which tier of proposal to fetch. E.g. "CORRECT", "INCORRECT_EASY", etc.
            num_frames: Number of frames to retrieve: 2, 3, or 5.
                        (If only a single file is found, that single one is returned.)
            few_shot_count: 0 (no few-shot) or e.g. 2 or 4, indicating how many exemplars to pull.

        Returns:
            A dictionary with:
              {
                  "puzzle": <PuzzleSchema as dict>,
                  "proposal": <ProposalSchema as dict>,
                  "images": [list of image paths (str)],
                  "few_shot": [ { puzzle+proposal+images }, ... ]  # optional
              }
        """
        # 1) Retrieve puzzle:
        puzzle = self.db_manager.db["puzzles"].find_one({"id": puzzle_id})
        if not puzzle:
            raise ValueError(f"No puzzle found with id={puzzle_id}")

        # 2) Retrieve a matching proposal (e.g. CORRECT or INCORRECT)
        proposal = self.db_manager.db["proposals"].find_one(
            {"id": puzzle_id, "tier": proposal_tier}
        )
        if not proposal:
            raise ValueError(
                f"No proposal found with puzzle_id={puzzle_id}, tier={proposal_tier}"
            )

        # 3) Locate screenshot images (path could be a file or a directory)
        images_list = self._retrieve_images(proposal.get("image_path"), num_frames)

        # 4) Optionally retrieve few-shot exemplars
        few_shot_samples = []
        if few_shot_count > 0:
            # In real usage, you'd define logic for how you pick "few_shot_count" examples.
            # For example, random selection among proposals or a small curated set.
            # We demonstrate a random approach here, but you can refine as needed.
            few_shot_samples = self._get_few_shot_samples(few_shot_count)

        return {
            "puzzle": puzzle,
            "proposal": proposal,
            "images": images_list,
            "few_shot": few_shot_samples,
        }

    def _retrieve_images(self, image_path: str, num_frames: int) -> list[str]:
        """
        Given an 'image_path' which might be a single .png file or a directory,
        return the selected frames (first, middle, last, etc.).

        Args:
            image_path: Path as stored in proposals.image_path (could be "images/correct_proposals/00012_001/1.png")
            num_frames: 2 (start/end), 3, or 5, etc.

        Returns:
            A list of absolute or relative file paths (as strings) to the chosen screenshots.
        """
        p = Path(image_path)
        if p.is_file():
            # There's only one file, so we just return that
            return [str(p)]

        if not p.is_dir():
            # Try to see if it's relative to base dir
            possible_dir = self.images_base_dir / p
            if possible_dir.is_dir():
                p = possible_dir
            else:
                logger.warning(
                    f"Image path '{image_path}' is neither file nor dir. Returning empty list."
                )
                return []

        # Now 'p' is a directory. Let's get all .png inside, sorted
        all_images = sorted(p.glob("*.png"), key=lambda x: x.name)
        if not all_images:
            logger.warning(f"No .png files found in folder {p}")
            return []

        if num_frames <= 1:
            # If user mistakenly sets 1 or 0
            return [str(all_images[0])]

        if len(all_images) <= num_frames:
            # If the folder has fewer images than we want, just return them all
            return [str(x) for x in all_images]

        # Otherwise, pick frames from start, middle, end
        indices = self._compute_frame_indices(len(all_images), num_frames)
        selected = [all_images[i] for i in indices]
        return [str(s) for s in selected]

    def _compute_frame_indices(self, total: int, num_frames: int) -> list[int]:
        """
        Utility for picking (start, middle..., end) frames from a list of length 'total'.
        E.g. if total=10, num_frames=3 => [0, 4, 9]
        """
        if num_frames == 2:
            return [0, total - 1]
        # For 3 or 5 frames, we basically spread them out evenly
        if num_frames == 3:
            # start, mid, end
            return [0, total // 2, total - 1]
        if num_frames == 5:
            return [
                0,
                total // 4,
                total // 2,
                3 * total // 4,
                total - 1,
            ]
        # Fallback: evenly spaced
        step = total / (num_frames - 1)
        indices = [int(round(i * step)) for i in range(num_frames)]
        return indices

    def _get_few_shot_samples(self, few_shot_count: int) -> list[dict[str, Any]]:
        """
        Retrieve a random selection of puzzle+proposal+images for few-shot usage.
        For example, half can be correct, half incorrect. Adjust logic as needed.
        """
        # We'll do a naive approach: gather some random correct and incorrect from the DB.
        # Suppose we want half correct, half incorrect if possible.
        half = few_shot_count // 2
        remainder = few_shot_count - half
        # Grab some CORRECT
        correct_cursor = self.db_manager.db["proposals"].aggregate(
            [{"$match": {"tier": "CORRECT"}}, {"$sample": {"size": half}}]
        )
        # Grab some INCORRECT (just pick one type for demonstration)
        incorrect_cursor = self.db_manager.db["proposals"].aggregate(
            [
                {"$match": {"tier": {"$regex": "INCORRECT"}}},
                {"$sample": {"size": remainder}},
            ]
        )

        all_docs = list(correct_cursor) + list(incorrect_cursor)
        random.shuffle(all_docs)

        few_shot_data = []
        for doc in all_docs:
            puzzle_id = doc["id"]
            puzzle_doc = self.db_manager.db["puzzles"].find_one({"id": puzzle_id})
            images = self._retrieve_images(
                doc["image_path"], num_frames=2
            )  # Keep it short
            few_shot_data.append(
                {
                    "puzzle": puzzle_doc,
                    "proposal": doc,
                    "images": images,
                }
            )

        return few_shot_data
